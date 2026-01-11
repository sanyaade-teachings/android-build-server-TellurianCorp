#!/usr/bin/env bash
set -euo pipefail

echo "Android remote build helper installer"

prompt() {
  local var_name=$1
  local prompt_text=$2
  local default_value=${3:-}
  local input=""

  if [ -t 0 ]; then
    read -r -p "$prompt_text" input
  elif [ -t 1 ] && [ -r /dev/tty ]; then
    read -r -p "$prompt_text" input < /dev/tty
  fi

  if [ -z "$input" ] && [ -n "${default_value}" ]; then
    input="$default_value"
  fi

  printf -v "$var_name" '%s' "$input"
}

missing=()
for cmd in rsync ssh scp python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    missing+=("$cmd")
  fi
done

if [ ${#missing[@]} -ne 0 ]; then
  echo "Missing tools: ${missing[*]}"
  echo "Install them and re-run this installer."
  exit 1
fi

prompt LOCAL_PATH "Local project path (contains gradlew): "
if [ -z "${LOCAL_PATH:-}" ]; then
  echo "Local path is required."
  exit 1
fi

if [ ! -f "$LOCAL_PATH/gradlew" ]; then
  echo "Warning: gradlew not found at $LOCAL_PATH/gradlew"
  prompt CONTINUE_ANYWAY "Continue anyway? [y/N]: "
  if [[ ! "${CONTINUE_ANYWAY:-}" =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

prompt REMOTE "Remote SSH (user@host): "
if [ -z "${REMOTE:-}" ]; then
  echo "Remote SSH is required."
  exit 1
fi

prompt PROJECT_NAME "Project name (remote path will be /home/projects/<name>): "
if [ -z "${PROJECT_NAME:-}" ]; then
  echo "Project name is required."
  exit 1
fi

REMOTE_PATH="/home/projects/$PROJECT_NAME"

prompt BUILD_TYPE "Build type [debug]: " "debug"
BUILD_TYPE=${BUILD_TYPE,,}

prompt OUT_DIR "Local output dir [$LOCAL_PATH/remote-apk]: " "$LOCAL_PATH/remote-apk"

prompt EXTRA_ARGS "Extra Gradle args (optional): "

prompt DELETE_CHOICE "Use rsync --delete? [y/N]: "
RSYNC_DELETE=false
if [[ "${DELETE_CHOICE:-}" =~ ^[Yy]$ ]]; then
  RSYNC_DELETE=true
fi

WEB_DIR=$(pwd)

CONFIG_DIR="$HOME/.android-build"
mkdir -p "$CONFIG_DIR"
CONFIG_FILE="$CONFIG_DIR/config"

{
  printf 'LOCAL_PATH=%q\n' "$LOCAL_PATH"
  printf 'REMOTE=%q\n' "$REMOTE"
  printf 'REMOTE_PATH=%q\n' "$REMOTE_PATH"
  printf 'BUILD_TYPE=%q\n' "$BUILD_TYPE"
  printf 'OUT_DIR=%q\n' "$OUT_DIR"
  printf 'EXTRA_ARGS=%q\n' "$EXTRA_ARGS"
  printf 'RSYNC_DELETE=%q\n' "$RSYNC_DELETE"
  printf 'WEB_DIR=%q\n' "$WEB_DIR"
} > "$CONFIG_FILE"

HELPER="$CONFIG_DIR/remote-build.sh"
cat > "$HELPER" <<'HELPER_EOF'
#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="$HOME/.android-build/config"
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Config not found: $CONFIG_FILE"
  exit 1
fi

# shellcheck disable=SC1090
source "$CONFIG_FILE"

if [ -n "${1:-}" ]; then
  BUILD_TYPE="$1"
fi

case "$BUILD_TYPE" in
  debug|release) ;;
  *)
    echo "Build type must be 'debug' or 'release'."
    exit 1
    ;;
esac

RSYNC_OPTS=(-az --exclude .git)
if [ "$RSYNC_DELETE" = "true" ]; then
  RSYNC_OPTS+=(--delete)
fi

if [ ! -f "$LOCAL_PATH/gradlew" ]; then
  echo "gradlew not found at $LOCAL_PATH/gradlew"
  exit 1
fi

update_status() {
    local status=$1
    local progress=$2
    printf '{"status": "%s", "progress": %d}\n' "$status" "$progress" > "$WEB_DIR/status.json"
}

trap 'update_status "error" 0; echo "Build failed."; exit 1' ERR

update_status "preparing_remote" 10
echo "Preparing remote path..."
ssh "$REMOTE" "mkdir -p /home/projects; mkdir -p '$REMOTE_PATH'"

update_status "syncing" 25
echo "Syncing project..."
rsync "${RSYNC_OPTS[@]}" "$LOCAL_PATH/" "$REMOTE:$REMOTE_PATH/"

update_status "building" 50
echo "Building on server..."
REMOTE_CMD="source ~/.profile >/dev/null 2 outlandish || true; chmod +x '$REMOTE_PATH/gradlew'; cd '$REMOTE_PATH'; ./gradlew assemble${BUILD_TYPE^} $EXTRA_ARGS"
ssh "$REMOTE" "$REMOTE_CMD"

update_status "finding_apk" 75
APK_PATH=$(ssh "$REMOTE" "ls -t '$REMOTE_PATH'/app/build/outputs/apk/$BUILD_TYPE/*.apk 2>/dev/null | head -n1")
if [ -z "$APK_PATH" ]; then
  APK_PATH=$(ssh "$REMOTE" "find '$REMOTE_PATH' -path '*/build/outputs/apk/*/*.apk' -type f -print0 | xargs -0 -r ls -t 2>/dev/null | head -n1")
fi

if [ -z "$APK_PATH" ]; then
  update_status "error" 0
  echo "APK not found in build outputs."
  exit 1
fi

mkdir -p "$OUT_DIR"

update_status "downloading" 90
echo "Downloading $APK_PATH"
scp "$REMOTE:$APK_PATH" "$OUT_DIR/"

update_status "done" 100
echo "Done: $OUT_DIR/$(basename "$APK_PATH")"
HELPER_EOF

chmod +x "$HELPER"
chmod +x build.sh

echo "Installed: $HELPER"
echo "Run: $HELPER [debug|release]"

echo "Starting web server..."
(
  cd "$WEB_DIR"
  python3 server.py &
)
echo "Web interface available at http://localhost:8000"
