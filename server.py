
import http.server
import socketserver
import json
import subprocess
import logging
import os
import threading
import time
import shutil
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from http import HTTPStatus

logging.basicConfig(filename='server.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_PROJECT_DIR = Path("/home/projects")
STATUS_DIR = Path("status")
ARTIFACT_DIR = Path("artifacts")
LOGS_DIR = Path("logs")
DEVICE_FILE = Path("device.json")
BUILD_LOCK = threading.Lock()
ACTIVE_BUILDS = {}

# Android SDK environment
ANDROID_HOME = "/home/android/sdk"
BUILD_ENV = os.environ.copy()
BUILD_ENV["ANDROID_HOME"] = ANDROID_HOME
BUILD_ENV["ANDROID_SDK_ROOT"] = ANDROID_HOME
BUILD_ENV["PATH"] = f"{ANDROID_HOME}/platform-tools:{ANDROID_HOME}/cmdline-tools/latest/bin:{BUILD_ENV.get('PATH', '')}"


def ensure_dirs():
    STATUS_DIR.mkdir(exist_ok=True)
    ARTIFACT_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


def load_device():
    """Load device configuration. Supports both old format (single address) and new format (multiple devices)."""
    if not DEVICE_FILE.exists():
        return {"devices": [], "selected": None}
    try:
        with DEVICE_FILE.open("r") as f:
            data = json.load(f)
            # Migrate old format to new format
            if "address" in data and "devices" not in data:
                address = data.get("address", "")
                if address:
                    devices = [{"id": "default", "name": "Default Device", "address": address}]
                    migrated_data = {"devices": devices, "selected": "default"}
                    # Persist migration immediately
                    try:
                        with DEVICE_FILE.open("w") as wf:
                            json.dump(migrated_data, wf, indent=2)
                            wf.flush()
                            os.fsync(wf.fileno())
                        logging.info("Migrated device.json from old format to new format")
                    except Exception as e:
                        logging.error(f"Error migrating device file: {e}")
                    return migrated_data
                else:
                    return {"devices": [], "selected": None}
            return data
    except Exception as e:
        logging.error(f"Error loading device file: {e}")
        return {"devices": [], "selected": None}


def save_device(address=None, device_id=None, device_name=None, selected_id=None):
    """Save device configuration. Can add/update a device or set selected device."""
    try:
        data = load_device()
        
        if selected_id is not None:
            # Just update selected device
            data["selected"] = selected_id if selected_id in [d["id"] for d in data["devices"]] else None
        elif device_id and address:
            # Add or update a device
            devices = data.get("devices", [])
            # Check if device already exists
            device_index = next((i for i, d in enumerate(devices) if d["id"] == device_id), None)
            if device_index is not None:
                # Update existing device
                devices[device_index]["address"] = address
                if device_name:
                    devices[device_index]["name"] = device_name
                logging.info(f"Updated device {device_id}: {device_name} at {address}")
            else:
                # Add new device
                if not device_name:
                    device_name = f"Device {device_id}"
                devices.append({"id": device_id, "name": device_name, "address": address})
                logging.info(f"Adding new device {device_id}: {device_name} at {address}")
            data["devices"] = devices
            # Auto-select if no device is selected
            if not data.get("selected") and devices:
                data["selected"] = devices[0]["id"]
        elif address:
            # Legacy: save single address (backward compatibility)
            if not data.get("devices"):
                data["devices"] = [{"id": "default", "name": "Default Device", "address": address}]
                data["selected"] = "default"
            else:
                # Update first device or create default
                if data["devices"]:
                    data["devices"][0]["address"] = address
                else:
                    data["devices"] = [{"id": "default", "name": "Default Device", "address": address}]
                    data["selected"] = "default"
        
        # Ensure devices list exists
        if "devices" not in data:
            data["devices"] = []
        
        # Write to file with error handling
        try:
            with DEVICE_FILE.open("w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            logging.info(f"Successfully saved device configuration: {len(data.get('devices', []))} devices")
        except Exception as e:
            logging.error(f"Error writing device file: {e}")
            raise
        
        return data
    except Exception as e:
        logging.error(f"Error in save_device: {e}")
        raise


def get_selected_device_address():
    """Get the address of the currently selected device."""
    data = load_device()
    selected_id = data.get("selected")
    if not selected_id:
        return None
    devices = data.get("devices", [])
    device = next((d for d in devices if d["id"] == selected_id), None)
    return device["address"] if device else None


def remove_device(device_id):
    """Remove a device from the configuration."""
    data = load_device()
    devices = data.get("devices", [])
    devices = [d for d in devices if d["id"] != device_id]
    data["devices"] = devices
    # If removed device was selected, select first available or None
    if data.get("selected") == device_id:
        data["selected"] = devices[0]["id"] if devices else None
    with DEVICE_FILE.open("w") as f:
        json.dump(data, f, indent=2)
    return data


def project_path(project_name):
    if not project_name or "/" in project_name or "\\" in project_name:
        return None
    candidate = (BASE_PROJECT_DIR / project_name).resolve()
    base = BASE_PROJECT_DIR.resolve()
    if base == candidate or not str(candidate).startswith(str(base) + os.sep):
        return None
    if not candidate.is_dir():
        return None
    return candidate


def has_gradlew(path_obj):
    return (path_obj / "gradlew").is_file()


def status_path(project_name):
    return STATUS_DIR / f"{project_name}.json"


def load_status(project_name):
    path = status_path(project_name)
    if not path.exists():
        return {"status": "not_started", "progress": 0}
    try:
        with path.open("r") as f:
            return json.load(f)
    except Exception:
        return {"status": "unknown", "progress": 0}


def write_status(project_name, status, progress, message=None, artifact=None):
    payload = {
        "project": project_name,
        "status": status,
        "progress": progress,
        "timestamp": int(time.time()),
    }
    if message:
        payload["message"] = message
    if artifact:
        payload["artifact"] = artifact
    path = status_path(project_name)
    with path.open("w") as f:
        json.dump(payload, f)


def list_projects():
    if not BASE_PROJECT_DIR.exists():
        return []
    projects = []
    for entry in sorted(BASE_PROJECT_DIR.iterdir()):
        if entry.is_dir() and has_gradlew(entry):
            projects.append(entry.name)
    return projects


def find_latest_apk(project_dir, build_type):
    apk_root = project_dir / "app" / "build" / "outputs" / "apk" / build_type
    if apk_root.exists():
        candidates = list(apk_root.glob("*.apk"))
    else:
        candidates = list(project_dir.glob("**/build/outputs/apk/**/*.apk"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def build_log_path(project_name):
    return LOGS_DIR / f"{project_name}.log"


def save_build_log(project_name, log_content):
    """Save build log to file."""
    log_path = build_log_path(project_name)
    with log_path.open("w", encoding="utf-8") as f:
        f.write(log_content)


def get_build_log(project_name):
    """Retrieve build log for a project."""
    log_path = build_log_path(project_name)
    if not log_path.exists():
        return None
    try:
        with log_path.open("r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def run_build(project_name, build_type):
    project_dir = project_path(project_name)
    if not project_dir:
        return

    log_output = []
    
    try:
        write_status(project_name, "preparing", 10)
        gradlew = project_dir / "gradlew"
        subprocess.run(["chmod", "+x", str(gradlew)], check=True)

        write_status(project_name, "building", 40)
        cmd = [str(gradlew), f"assemble{build_type.capitalize()}"]
        
        # Capture build output (don't use check=True so we can capture output on failure)
        process = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=BUILD_ENV
        )
        
        # Save build output (last 2000 lines to avoid huge files)
        combined_output = (process.stdout or "") + "\n" + (process.stderr or "")
        output_lines = combined_output.splitlines()
        log_content = "\n".join(output_lines[-2000:])
        save_build_log(project_name, log_content)
        
        # Now check if it failed
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, process.stdout, process.stderr)

        write_status(project_name, "finding_apk", 75)
        latest_apk = find_latest_apk(project_dir, build_type)
        if not latest_apk:
            write_status(project_name, "error", 0, message="APK not found in build outputs.")
            return

        project_artifacts = ARTIFACT_DIR / project_name
        project_artifacts.mkdir(parents=True, exist_ok=True)
        target_path = project_artifacts / latest_apk.name
        shutil.copy2(str(latest_apk), str(target_path))

        artifact_url = f"/artifacts/{project_name}/{latest_apk.name}"
        write_status(project_name, "done", 100, artifact=artifact_url)
    except subprocess.CalledProcessError as e:
        # Capture failed build output
        try:
            # Try to get stderr if available
            error_output = e.stderr if hasattr(e, 'stderr') and e.stderr else ""
            stdout_output = e.stdout if hasattr(e, 'stdout') and e.stdout else ""
            log_content = f"{stdout_output}\n{error_output}".strip()
            if not log_content:
                log_content = str(e)
            save_build_log(project_name, log_content)
        except Exception:
            save_build_log(project_name, str(e))
        
        logging.error("Build failed for %s: %s", project_name, e)
        write_status(project_name, "error", 0, message="Build failed. View logs for details.")
    except Exception as e:
        save_build_log(project_name, f"Unexpected error: {str(e)}")
        logging.error("Unexpected build error for %s: %s", project_name, e)
        write_status(project_name, "error", 0, message="Unexpected error. View logs for details.")
    finally:
        with BUILD_LOCK:
            ACTIVE_BUILDS.pop(project_name, None)


def run_clean_cache(project_name):
    """Clean Gradle cache for a project."""
    project_dir = project_path(project_name)
    if not project_dir:
        return

    try:
        write_status(project_name, "cleaning", 10, message="Cleaning Gradle cache...")
        gradlew = project_dir / "gradlew"
        subprocess.run(["chmod", "+x", str(gradlew)], check=True)

        # Run gradle clean
        write_status(project_name, "cleaning", 50, message="Running gradle clean...")
        process = subprocess.run(
            [str(gradlew), "clean"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=BUILD_ENV
        )

        # Save output
        combined_output = (process.stdout or "") + "\n" + (process.stderr or "")
        save_build_log(project_name, combined_output)

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, ["gradlew", "clean"])

        # Also clean .gradle directory in project
        gradle_cache = project_dir / ".gradle"
        if gradle_cache.exists():
            shutil.rmtree(str(gradle_cache), ignore_errors=True)

        # Clean build directory
        build_dir = project_dir / "build"
        if build_dir.exists():
            shutil.rmtree(str(build_dir), ignore_errors=True)

        app_build_dir = project_dir / "app" / "build"
        if app_build_dir.exists():
            shutil.rmtree(str(app_build_dir), ignore_errors=True)

        write_status(project_name, "done", 100, message="Cache cleaned successfully.")
    except subprocess.CalledProcessError as e:
        logging.error("Clean cache failed for %s: %s", project_name, e)
        write_status(project_name, "error", 0, message="Clean cache failed. View logs for details.")
    except Exception as e:
        save_build_log(project_name, f"Unexpected error: {str(e)}")
        logging.error("Unexpected clean error for %s: %s", project_name, e)
        write_status(project_name, "error", 0, message="Unexpected error. View logs for details.")
    finally:
        with BUILD_LOCK:
            ACTIVE_BUILDS.pop(project_name, None)


def latest_artifact_path(project_name):
    project_artifacts = ARTIFACT_DIR / project_name
    if project_artifacts.exists():
        artifacts = list(project_artifacts.glob("*.apk"))
        if artifacts:
            artifacts.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return artifacts[0]
    return None


def find_adb():
    """Find adb executable in common locations or PATH."""
    # Common Android SDK locations
    common_paths = [
        "/home/android/sdk/platform-tools/adb",
        os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
        os.path.expanduser("~/sdk/platform-tools/adb"),
        "/opt/android-sdk/platform-tools/adb",
    ]
    
    # Check common paths first
    for path in common_paths:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    
    # Check PATH
    adb_path = shutil.which("adb")
    if adb_path:
        return adb_path
    
    return None


def run_pair_device(pair_address, pairing_code):
    """Pair with a device using wireless debugging pairing code (Android 11+)."""
    adb_path = find_adb()
    if not adb_path:
        return {"success": False, "message": "ADB not found. Please install Android SDK platform-tools."}

    try:
        # Run adb pair command
        result = subprocess.run(
            [adb_path, "pair", pair_address, pairing_code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30
        )
        
        output = (result.stdout or "") + (result.stderr or "")
        
        if result.returncode == 0 and "Successfully paired" in output:
            logging.info("Successfully paired with device at %s", pair_address)
            return {"success": True, "message": "Successfully paired with device!"}
        else:
            logging.error("Pairing failed for %s: %s", pair_address, output)
            return {"success": False, "message": f"Pairing failed: {output.strip()}"}
    except subprocess.TimeoutExpired:
        return {"success": False, "message": "Pairing timed out. Please check the pairing code and try again."}
    except Exception as e:
        logging.error("Unexpected pairing error: %s", e)
        return {"success": False, "message": f"Unexpected error: {str(e)}"}


def run_deploy(project_name, device_addr, build_type=None):
    if not device_addr:
        write_status(project_name, "error", 0, message="Device address not set.")
        return

    project_dir = project_path(project_name)
    if not project_dir:
        return

    adb_path = find_adb()
    if not adb_path:
        error_msg = "ADB not found. Please install Android SDK platform-tools."
        logging.error("ADB not found for deployment of %s", project_name)
        write_status(project_name, "error", 0, message=error_msg)
        return

    deploy_log = []
    
    try:
        write_status(project_name, "connecting_device", 10)
        connect_result = subprocess.run(
            [adb_path, "connect", device_addr],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        deploy_log.append(f"Connecting to device {device_addr}:")
        deploy_log.append(connect_result.stdout)
        if connect_result.stderr:
            deploy_log.append(connect_result.stderr)
        connect_result.check_returncode()

        apk_path = latest_artifact_path(project_name)
        if not apk_path and build_type:
            latest_apk = find_latest_apk(project_dir, build_type)
            if latest_apk:
                project_artifacts = ARTIFACT_DIR / project_name
                project_artifacts.mkdir(parents=True, exist_ok=True)
                apk_path = project_artifacts / latest_apk.name
                shutil.copy2(str(latest_apk), str(apk_path))

        if not apk_path:
            write_status(project_name, "error", 0, message="No APK available to deploy.")
            return

        # Ensure absolute path
        apk_path = Path(apk_path).resolve()
        if not apk_path.exists():
            write_status(project_name, "error", 0, message=f"APK file not found: {apk_path}")
            return

        write_status(project_name, "installing_apk", 70)
        install_result = subprocess.run(
            [adb_path, "install", "-r", str(apk_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        deploy_log.append(f"\nInstalling APK {apk_path.name}:")
        deploy_log.append(install_result.stdout)
        if install_result.stderr:
            deploy_log.append(install_result.stderr)
        
        # Save deploy log
        log_content = "\n".join(deploy_log)
        save_build_log(project_name, log_content)  # Reuse build log storage for deploy logs
        
        install_result.check_returncode()
        write_status(project_name, "deployed", 100, message="APK installed on device.")
    except subprocess.CalledProcessError as e:
        # Capture failed deploy output
        deploy_log.append(f"\nError: {str(e)}")
        if hasattr(e, 'stdout') and e.stdout:
            deploy_log.append(f"stdout: {e.stdout}")
        if hasattr(e, 'stderr') and e.stderr:
            deploy_log.append(f"stderr: {e.stderr}")
        
        log_content = "\n".join(deploy_log)
        save_build_log(project_name, log_content)
        
        logging.error("Deploy failed for %s: %s", project_name, e)
        write_status(project_name, "error", 0, message="Deploy failed. View logs for details.")
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        deploy_log.append(error_msg)
        save_build_log(project_name, "\n".join(deploy_log))
        logging.error("Unexpected deploy error for %s: %s", project_name, e)
        write_status(project_name, "error", 0, message="Unexpected error. View logs for details.")


class Handler(http.server.SimpleHTTPRequestHandler):
    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        logging.info(f"GET request for {self.path}")
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.path = 'index.html'
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        elif parsed.path == '/api/projects':
            self._send_json({"projects": list_projects()})
        elif parsed.path == '/api/device':
            self._send_json(load_device())
        elif parsed.path == '/api/status':
            params = parse_qs(parsed.query)
            project = params.get("project", [""])[0]
            project_dir = project_path(project)
            if not project_dir:
                self._send_json({"error": "Invalid project."}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json(load_status(project))
        elif parsed.path == '/api/logs':
            try:
                params = parse_qs(parsed.query)
                project = params.get("project", [""])[0]
                if not project:
                    self._send_json({"error": "Project parameter required."}, status=HTTPStatus.BAD_REQUEST)
                    return
                project_dir = project_path(project)
                if not project_dir:
                    self._send_json({"error": "Invalid project."}, status=HTTPStatus.BAD_REQUEST)
                    return
                log_content = get_build_log(project)
                if log_content is None:
                    self._send_json({"error": "No logs available."}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json({"logs": log_content})
                return
            except Exception as e:
                logging.error(f"Error retrieving logs: {e}")
                self._send_json({"error": "Failed to retrieve logs."}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
        else:
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        logging.info(f"POST request for {self.path}")
        if self.path == '/api/start-build':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                project = data.get("project", "")
                build_type = data.get("build_type", "debug").lower()

                if build_type not in ("debug", "release"):
                    self._send_json({"error": "Build type must be debug or release."}, status=HTTPStatus.BAD_REQUEST)
                    return

                project_dir = project_path(project)
                if not project_dir or not has_gradlew(project_dir):
                    self._send_json({"error": "Project not found or missing gradlew."}, status=HTTPStatus.BAD_REQUEST)
                    return

                with BUILD_LOCK:
                    if project in ACTIVE_BUILDS:
                        self._send_json({"message": "Build already running."})
                        return
                    t = threading.Thread(target=run_build, args=(project, build_type), daemon=True)
                    ACTIVE_BUILDS[project] = t
                    t.start()

                self._send_json({"message": "Build started"})
            except json.JSONDecodeError:
                logging.error("Invalid JSON in POST request")
                self._send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            except Exception as e:
                logging.error(f"Error processing POST request: {e}")
                self._send_json({"error": "Server error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        elif self.path == '/api/device':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                
                # Handle different operations
                if "action" in data:
                    action = data.get("action")
                    if action == "add":
                        address = data.get("address", "").strip()
                        device_id = data.get("device_id", "").strip() or f"device_{int(time.time())}"
                        device_name = data.get("device_name", "").strip() or f"Device {device_id}"
                        if not address:
                            self._send_json({"error": "Device address is required."}, status=HTTPStatus.BAD_REQUEST)
                            return
                        if " " in address:
                            self._send_json({"error": "Invalid device address."}, status=HTTPStatus.BAD_REQUEST)
                            return
                        result = save_device(address=address, device_id=device_id, device_name=device_name)
                        self._send_json(result)
                    elif action == "remove":
                        device_id = data.get("device_id", "").strip()
                        if not device_id:
                            self._send_json({"error": "Device ID is required."}, status=HTTPStatus.BAD_REQUEST)
                            return
                        result = remove_device(device_id)
                        self._send_json(result)
                    elif action == "select":
                        selected_id = data.get("device_id", "").strip()
                        result = save_device(selected_id=selected_id)
                        self._send_json(result)
                    else:
                        self._send_json({"error": "Unknown action."}, status=HTTPStatus.BAD_REQUEST)
                else:
                    # Legacy: single address (backward compatibility)
                    address = data.get("address", "").strip()
                    if address and " " in address:
                        self._send_json({"error": "Invalid device address."}, status=HTTPStatus.BAD_REQUEST)
                        return
                    result = save_device(address=address)
                    self._send_json(result)
            except json.JSONDecodeError:
                logging.error("Invalid JSON in POST request")
                self._send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            except Exception as e:
                logging.error(f"Error processing POST request: {e}")
                self._send_json({"error": "Server error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        elif self.path == '/api/deploy':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                project = data.get("project", "")
                build_type = data.get("build_type", "debug").lower()
                project_dir = project_path(project)
                if not project_dir:
                    self._send_json({"error": "Project not found."}, status=HTTPStatus.BAD_REQUEST)
                    return
                device_addr = get_selected_device_address()
                if not device_addr:
                    self._send_json({"error": "No device selected. Please select a device first."}, status=HTTPStatus.BAD_REQUEST)
                    return
                t = threading.Thread(
                    target=run_deploy,
                    args=(project, device_addr, build_type),
                    daemon=True,
                )
                t.start()
                self._send_json({"message": "Deploy started"})
            except json.JSONDecodeError:
                logging.error("Invalid JSON in POST request")
                self._send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            except Exception as e:
                logging.error(f"Error processing POST request: {e}")
                self._send_json({"error": "Server error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        elif self.path == '/api/clean-cache':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                project = data.get("project", "")
                project_dir = project_path(project)
                if not project_dir or not has_gradlew(project_dir):
                    self._send_json({"error": "Project not found or missing gradlew."}, status=HTTPStatus.BAD_REQUEST)
                    return

                with BUILD_LOCK:
                    if project in ACTIVE_BUILDS:
                        self._send_json({"message": "Build already running."})
                        return
                    t = threading.Thread(target=run_clean_cache, args=(project,), daemon=True)
                    ACTIVE_BUILDS[project] = t
                    t.start()

                self._send_json({"message": "Clean cache started"})
            except json.JSONDecodeError:
                logging.error("Invalid JSON in POST request")
                self._send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            except Exception as e:
                logging.error(f"Error processing POST request: {e}")
                self._send_json({"error": "Server error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        elif self.path == '/api/pair-device':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data)
                pair_address = data.get("pair_address", "").strip()
                pairing_code = data.get("pairing_code", "").strip()
                
                if not pair_address:
                    self._send_json({"error": "Pair address is required (e.g., 192.168.1.20:37123)"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if not pairing_code:
                    self._send_json({"error": "Pairing code is required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if " " in pair_address or " " in pairing_code:
                    self._send_json({"error": "Invalid pair address or pairing code"}, status=HTTPStatus.BAD_REQUEST)
                    return
                
                result = run_pair_device(pair_address, pairing_code)
                if result["success"]:
                    self._send_json(result)
                else:
                    self._send_json(result, status=HTTPStatus.BAD_REQUEST)
            except json.JSONDecodeError:
                logging.error("Invalid JSON in POST request")
                self._send_json({"error": "Invalid JSON"}, status=HTTPStatus.BAD_REQUEST)
            except Exception as e:
                logging.error(f"Error processing pair request: {e}")
                self._send_json({"error": "Server error"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


PORT = 8000
try:
    ensure_dirs()
    with ReusableTCPServer(("0.0.0.0", PORT), Handler) as httpd:
        logging.info(f"Serving at port {PORT}")
        print(f"serving at port {PORT}")
        httpd.serve_forever()
except Exception as e:
    logging.error(f"Failed to start server: {e}")
    print(f"Failed to start server: {e}")
