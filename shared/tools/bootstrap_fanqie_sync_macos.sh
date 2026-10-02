#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/Tyr1onX/novel-workspace"
PUBLISHER_REPO="https://github.com/rockbenben/fanqie-publisher.git"
PINNED_COMMIT="91d8efe487c441b516e0ffa1986f7c5b73a1c0a9"

ROOT_DIR="${NOVEL_WORKSPACE_HOME:-$HOME/.novel-workspace}"
RUNTIME_DIR="${FANQIE_RUNTIME_DIR:-$ROOT_DIR/fanqie-publisher}"
VENV_DIR="${FANQIE_VENV_DIR:-$ROOT_DIR/fanqie-venv}"
RUNNER_DIR="${FANQIE_RUNNER_DIR:-$ROOT_DIR/github-runner}"
RUNNER_NAME="${FANQIE_RUNNER_NAME:-$(scutil --get ComputerName 2>/dev/null || hostname)-fanqie}"
SKIP_LOGIN=0

if [[ "${1:-}" == "--skip-login" ]]; then
  SKIP_LOGIN=1
elif [[ -n "${1:-}" ]]; then
  echo "Usage: bash shared/tools/bootstrap_fanqie_sync_macos.sh [--skip-login]"
  exit 2
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This bootstrap is for macOS."
  exit 1
fi

for command in python3 git curl tar; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing required command: $command"
    exit 1
  fi
done

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10+ is required.")
PY

mkdir -p "$ROOT_DIR"

echo "=== 1/3 Install pinned Fanqie runtime ==="
if [[ ! -d "$RUNTIME_DIR/.git" ]]; then
  git clone "$PUBLISHER_REPO" "$RUNTIME_DIR"
fi

git -C "$RUNTIME_DIR" fetch origin --tags --prune
git -C "$RUNTIME_DIR" checkout --detach "$PINNED_COMMIT"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r "$RUNTIME_DIR/requirements.txt"
"$PYTHON" -m playwright install chromium

if (( SKIP_LOGIN == 0 )); then
  echo
  echo "A Chromium window will open. Log in to Fanqie once, then let the command save the session."
  (
    cd "$RUNTIME_DIR"
    "$PYTHON" fanqie_upload.py login
  )
fi

echo
echo "=== 2/3 Install GitHub self-hosted runner ==="
case "$(uname -m)" in
  arm64) runner_arch="arm64" ;;
  x86_64) runner_arch="x64" ;;
  *)
    echo "Unsupported Mac architecture: $(uname -m)"
    exit 1
    ;;
esac

mkdir -p "$RUNNER_DIR"
if [[ ! -f "$RUNNER_DIR/config.sh" ]]; then
  release_json="$(curl -fsSL     -H "Accept: application/vnd.github+json"     -H "User-Agent: novel-workspace-bootstrap"     https://api.github.com/repos/actions/runner/releases/latest)"

  asset_url="$(printf '%s' "$release_json" | "$PYTHON" -c '
import json, sys
data = json.load(sys.stdin)
needle = "actions-runner-osx-" + sys.argv[1] + "-"
for asset in data.get("assets", []):
    name = asset.get("name", "")
    if name.startswith(needle) and name.endswith(".tar.gz"):
        print(asset["browser_download_url"])
        break
else:
    raise SystemExit("Could not locate matching macOS GitHub Actions runner asset.")
' "$runner_arch")"

  archive="$(mktemp -t fanqie-runner).tar.gz"
  trap 'rm -f "$archive"' EXIT
  curl -fL "$asset_url" -o "$archive"
  tar -xzf "$archive" -C "$RUNNER_DIR"
  rm -f "$archive"
  trap - EXIT
fi

if [[ ! -f "$RUNNER_DIR/.runner" ]]; then
  token="${GITHUB_RUNNER_TOKEN:-}"
  if [[ -z "$token" ]]; then
    echo
    echo "Open GitHub -> Tyr1onX/novel-workspace -> Settings -> Actions -> Runners -> New self-hosted runner."
    echo "Copy the short-lived registration token. It is only used locally and is not saved."
    read -r -s -p "Runner registration token: " token
    echo
  fi
  if [[ -z "$token" ]]; then
    echo "Runner registration token is required."
    exit 1
  fi

  (
    cd "$RUNNER_DIR"
    ./config.sh --unattended       --url "$REPO_URL"       --token "$token"       --name "$RUNNER_NAME"       --labels "fanqie"       --work "_work"       --replace
  )
  unset token GITHUB_RUNNER_TOKEN
else
  echo "GitHub runner is already configured."
fi

echo
echo "=== 3/3 Install macOS launchd service ==="
(
  cd "$RUNNER_DIR"
  if [[ ! -f ".service" ]]; then
    ./svc.sh install
  fi
  ./svc.sh start >/dev/null 2>&1 || true
  ./svc.sh status
)

echo
echo "Bootstrap complete."
echo "Runtime: $RUNTIME_DIR"
echo "Python:  $PYTHON"
echo "Runner:  $RUNNER_DIR"
echo "The runner now starts through the official macOS launchd service."
