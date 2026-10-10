#!/usr/bin/env python3
"""Preserve unrelated shell config; manage only explicitly marked blocks/files."""
import argparse
import os
from pathlib import Path
import shutil
import time

MARK = '# Managed by linux-dev-bootstrap'
START = '# >>> linux-dev-bootstrap >>>'
END = '# <<< linux-dev-bootstrap <<<'
ENV = '''# Managed by linux-dev-bootstrap
# PATH-only setup is safe to source from noninteractive shells.
for _dev_bin in "$HOME/bin" "$HOME/.local/bin"; do
    case ":$PATH:" in *":$_dev_bin:"*) ;; *) PATH="$_dev_bin:$PATH";; esac
done
export PATH
unset _dev_bin
'''
BASH = '''# Managed by linux-dev-bootstrap
[[ $- == *i* ]] || return 0
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if ! declare -F nvm >/dev/null && [[ -s $NVM_DIR/nvm.sh ]]; then
    source "$NVM_DIR/nvm.sh"
fi
if [[ -s $NVM_DIR/bash_completion ]]; then source "$NVM_DIR/bash_completion"; fi
if ! declare -F ble-attach >/dev/null && [[ -r $HOME/.local/share/blesh/ble.sh ]]; then
    source -- "$HOME/.local/share/blesh/ble.sh"
fi
'''
RUN = '''#!/usr/bin/env bash
# Managed by linux-dev-bootstrap
set -eo pipefail
source "$HOME/.config/jayson-dev/env.sh"
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [[ -s $NVM_DIR/nvm.sh ]]; then source "$NVM_DIR/nvm.sh"; fi
if (($# == 0)); then echo 'Usage: dev-run COMMAND [ARGS...]' >&2; exit 2; fi
exec "$@"
'''

def configure(home, source=None):
    home = Path(home)
    backup = home / '.local/state/jayson-dev/backups' / str(time.time_ns())
    files = {home/'.config/jayson-dev/env.sh': ENV,
             home/'.config/jayson-dev/bash.sh': BASH,
             home/'.local/bin/dev-run': RUN}
    source=Path(source) if source else Path(__file__).resolve().parents[1]
    files[home/'.local/bin/dev-doctor']=(source/'doctor.sh').read_text()
    files[home/'.local/share/jayson-dev/doctor.py']=(source/'scripts/doctor.py').read_text()
    bash_hook = '''[ ! -r "$HOME/.config/jayson-dev/env.sh" ] || . "$HOME/.config/jayson-dev/env.sh"
if [ -n "${BASH_VERSION:-}" ] && [ -r "$HOME/.config/jayson-dev/bash.sh" ]; then
    . "$HOME/.config/jayson-dev/bash.sh"
fi'''
    login = next((home/n for n in ['.bash_profile','.bash_login'] if (home/n).exists()), home/'.profile')
    hooks = {home/'.bashrc': bash_hook,
             login: '[ ! -r "$HOME/.config/jayson-dev/env.sh" ] || . "$HOME/.config/jayson-dev/env.sh"'}
    # Validate all targets before changing anything.
    planned = []
    for path, text in files.items():
        old = path.read_text() if path.exists() else None
        if old is not None and MARK not in old.splitlines()[:2]:
            raise RuntimeError(f'Refusing to replace unrecognized file: {path}')
        planned.append((path, old, text))
    for path, text in hooks.items():
        old = path.read_text() if path.exists() else ''
        if old.count(START) != old.count(END) or old.count(START) > 1:
            raise RuntimeError(f'Invalid managed markers in {path}; no files changed')
        block = START+'\n'+text+'\n'+END
        if START in old:
            a, b = old.index(START), old.index(END)
            if b < a: raise RuntimeError(f'Reversed managed markers: {path}')
            new = old[:a]+block+old[b+len(END):]
        else: new = old+('' if not old or old.endswith('\n') else '\n')+block+'\n'
        planned.append((path, old if path.exists() else None, new))
    for path, old, new in planned:
        if old == new: continue
        if old is not None:
            backup.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(backup,0o700)
            saved = backup / str(path.relative_to(home)).replace('/', '__')
            shutil.copy2(path,saved)
            saved.chmod(0o600)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(new)
        if path.name in ('dev-run','dev-doctor'): path.chmod(0o755)
        print(f'Configured: {path}')
    # Provide fd on distributions that package it as fdfind; never replace an existing command.
    target=home/'.local/bin/fd'
    if shutil.which('fd') is None and shutil.which('fdfind') and not target.exists() and not target.is_symlink():
        target.symlink_to(shutil.which('fdfind'))
    if backup.exists(): print(f'Backups: {backup}')

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--home',type=Path,required=True)
    parser.add_argument('--agents',type=Path)
    args=parser.parse_args()
    configure(args.home)
    if args.agents:
        target=args.home / ".codex/AGENTS.md"
        if target.exists() or target.is_symlink():
            print(f"Preserved existing agent instructions: {target}")
        else:
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(args.agents.read_text())
            print(f"Installed portable agent instructions: {target}")
