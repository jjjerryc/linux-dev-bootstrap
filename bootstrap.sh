#!/usr/bin/env bash
# Install a portable user environment; never changes authentication or services.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
dry_run=0; system_packages=1; config_only=0; with_agents=0
install_uv=1; install_node=1; install_blesh=1; install_codex=1
node_version=24; nvm_version=v0.40.8; uv_version=0.12.23; codex_version=0.161.0
usage() {
  cat <<'HELP'
Usage: bash bootstrap.sh [options]
  --dry-run              Print the plan; no downloads or writes
  --user-only            Skip sudo/system packages (administrator provides prerequisites)
  --system-packages      Use sudo apt/dnf for base tools (default)
  --config-only          Only install managed shell configuration
  --with-agents          Add portable Codex AGENTS.md only if none already exists
  --no-uv --no-node --no-blesh --no-codex
  --node-version VERSION    Default: 24 (latest installed/available patch in major 24)
  --codex-version VERSION   Default: 0.161.0; accepts latest
  --help
Default: sudo system tools + user-local uv, ble.sh, nvm/Node 24 and Codex CLI; preserve existing tools.
HELP
}
while (($#)); do
  case "$1" in
    --dry-run) dry_run=1;;
    --system-packages) system_packages=1;;
    --user-only) system_packages=0;;
    --config-only) config_only=1;;
    --with-agents) with_agents=1;;
    --no-uv) install_uv=0;; --no-node) install_node=0;install_codex=0;;
    --no-blesh) install_blesh=0;; --no-codex) install_codex=0;;
    --node-version|--codex-version)
      (($# >= 2)) || { echo "Missing value: $1" >&2; exit 2; }
      [[ $2 =~ ^[a-zA-Z0-9.v-]+$ ]] || { echo 'Invalid version' >&2; exit 2; }
      if [[ $1 == --node-version ]]; then node_version=$2; else codex_version=$2; fi
      shift;;
    --help|-h) usage;exit 0;;
    *) echo "Unknown option: $1" >&2;usage >&2;exit 2;;
  esac
  shift
done
[[ $(uname -s) == Linux ]] || { echo 'Linux is required.' >&2; exit 1; }
printf 'Target: %s\nSystem packages: %s; config only: %s\nuv: %s; ble.sh: %s; Node %s: %s; Codex %s: %s\n' \
  "$HOME" "$system_packages" "$config_only" "$install_uv" "$install_blesh" "$node_version" "$install_node" "$codex_version" "$install_codex"
if ((dry_run)); then
  echo 'Would preserve existing tools, add managed Bash/PATH hooks with backups, and install missing selected tools.'
  echo 'System tools: git curl python3 tar xz gawk tmux rg fd/fdfind rsync.'
  echo 'No CUDA/Docker/SSH configuration, credentials, services, or compute workloads are included.'
  exit 0
fi
if ((system_packages && !config_only)); then
  command -v sudo >/dev/null || { echo 'sudo is unavailable; ask the administrator for prerequisites.' >&2;exit 1; }
  if command -v apt-get >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl git python3 tar xz-utils gawk tmux ripgrep fd-find rsync
  elif command -v dnf >/dev/null; then
    sudo dnf install -y ca-certificates curl git python3 tar xz gawk tmux ripgrep fd-find rsync
  else echo 'Supported system package managers: apt-get and dnf. Install prerequisites manually.' >&2;exit 1;fi
fi
command -v python3 >/dev/null || { echo 'python3 is required for safe configuration updates.' >&2;exit 1; }
if ((!config_only)); then
  missing=()
  for tool in curl git tar xz; do command -v "$tool" >/dev/null || missing+=("$tool");done
  if ((${#missing[@]})); then printf 'Missing prerequisites: %s\n' "${missing[*]}" >&2;exit 1;fi
  task_tmp=$(mktemp -d "${TMPDIR:-/tmp}/jayson-dev.XXXXXXXX")
  trap 'rm -rf -- "$task_tmp"' EXIT
  download() { curl --fail --location --silent --show-error --proto '=https' --proto-redir '=https' --retry 2 --connect-timeout 15 --max-time 180 "$1" -o "$2"; }
  export PATH="$HOME/.local/bin:$PATH"
  if ((install_uv)); then
    if command -v uv >/dev/null; then echo "Reuse uv: $(command -v uv)"
    else
      download "https://astral.sh/uv/$uv_version/install.sh" "$task_tmp/uv-install.sh"
      UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh "$task_tmp/uv-install.sh"
    fi
  fi
  if ((install_blesh)); then
    if [[ -f $HOME/.local/share/blesh/ble.sh ]]; then echo 'Reuse ble.sh'
    else
      command -v gawk >/dev/null || { echo 'ble.sh needs gawk; install it first.' >&2;exit 1; }
      download 'https://github.com/akinomyoga/ble.sh/releases/download/nightly/ble-nightly.tar.xz' "$task_tmp/ble.tar.xz"
      tar -xJf "$task_tmp/ble.tar.xz" -C "$task_tmp"
      bash "$task_tmp/ble-nightly/ble.sh" --install "$HOME/.local/share"
    fi
  fi
  if ((install_node)); then
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [[ ! -s $NVM_DIR/nvm.sh ]]; then
      if [[ -e $NVM_DIR ]] && [[ -n $(ls -A -- "$NVM_DIR") ]]; then echo "Unrecognized nonempty nvm directory: $NVM_DIR" >&2;exit 1;fi
      download "https://raw.githubusercontent.com/nvm-sh/nvm/$nvm_version/install.sh" "$task_tmp/nvm-install.sh"
      PROFILE=/dev/null NVM_DIR="$NVM_DIR" bash "$task_tmp/nvm-install.sh"
    fi
    # Upstream nvm is not guaranteed to be nounset-safe.
    set +u
    source "$NVM_DIR/nvm.sh" --no-use
    selected_node=$(nvm version "$node_version" || true)
    if [[ $selected_node == N/A ]]; then nvm install "$node_version"; else nvm use "$selected_node"; fi
    if [[ ! -e $NVM_DIR/alias/default ]]; then nvm alias default "$node_version"; fi
    set -u
    if ((install_codex)); then
      # Node lives under the user's nvm directory, so this global CLI install is user-local.
      if command -v codex >/dev/null; then echo "Reuse Codex: $(command -v codex)"
      else
        npm_prefix=$(npm prefix -g)
        case "$npm_prefix/" in "$NVM_DIR/"*) ;; *) echo "Refusing npm install outside nvm: $npm_prefix" >&2;exit 1;; esac
        npm install -g "@openai/codex@$codex_version"
      fi
    fi
  fi
fi
config_args=(--home "$HOME")
if ((with_agents)); then config_args+=(--agents "$ROOT/config/AGENTS.md"); fi
python3 "$ROOT/scripts/configure.py" "${config_args[@]}"
echo 'Done. Open a new Bash terminal, then run ./doctor.sh.'
echo 'For noninteractive SSH: ~/.local/bin/dev-run uv --version (or codex --version).'
