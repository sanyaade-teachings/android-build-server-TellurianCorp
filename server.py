
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
    if not DEVICE_FILE.exists():
        return {"address": ""}
    try:
        with DEVICE_FILE.open("r") as f:
            return json.load(f)
    except Exception:
        return {"address": ""}


def save_device(address):
    payload = {"address": address}
    with DEVICE_FILE.open("w") as f:
        json.dump(payload, f)
    return payload


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
                address = data.get("address", "").strip()
                if address and " " in address:
                    self._send_json({"error": "Invalid device address."}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(save_device(address))
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
                device = load_device()
                t = threading.Thread(
                    target=run_deploy,
                    args=(project, device.get("address", ""), build_type),
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
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()


PORT = 8000
try:
    ensure_dirs()
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        logging.info(f"Serving at port {PORT}")
        print(f"serving at port {PORT}")
        httpd.serve_forever()
except Exception as e:
    logging.error(f"Failed to start server: {e}")
    print(f"Failed to start server: {e}")
