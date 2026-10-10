#!/usr/bin/env bash
# Managed by linux-dev-bootstrap
set -eo pipefail
if [[ -r $HOME/.config/jayson-dev/env.sh ]]; then source "$HOME/.config/jayson-dev/env.sh"; fi
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -s $NVM_DIR/nvm.sh ]]; then
  source "$NVM_DIR/nvm.sh"
  export DEV_DOCTOR_NVM_VERSION="$(nvm --version)"
fi
doctor_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ -f $doctor_root/scripts/doctor.py ]]; then
  exec python3 "$doctor_root/scripts/doctor.py" "$@"
else
  exec python3 "$HOME/.local/share/jayson-dev/doctor.py" "$@"
fi
