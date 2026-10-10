#!/usr/bin/env bash
set -uo pipefail
printf 'Host: %s | shell: %s\n' "$(hostname)" "${SHELL:-unknown}"
if [[ -r $HOME/.config/jayson-dev/env.sh ]]; then source "$HOME/.config/jayson-dev/env.sh"; fi
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -s $NVM_DIR/nvm.sh ]]; then set +u; source "$NVM_DIR/nvm.sh"; set -u; fi
missing=0
for tool in git curl python3 uv node npm codex tmux rg fd rsync gawk; do
  if command -v "$tool" >/dev/null; then printf '%-9s %s\n' "$tool" "$(command -v "$tool")"
  elif [[ $tool == fd ]] && command -v fdfind >/dev/null; then printf '%-9s %s\n' fd "$(command -v fdfind)"
  else printf '%-9s MISSING (install or intentionally omit)\n' "$tool";missing=1;fi
done
if [[ -r $HOME/.local/share/blesh/ble.sh ]]; then bash "$HOME/.local/share/blesh/ble.sh" --version
else echo 'ble.sh MISSING';missing=1;fi
for tool in uv node codex; do
  if command -v "$tool" >/dev/null; then "$tool" --version; fi
done
exit "$missing"
