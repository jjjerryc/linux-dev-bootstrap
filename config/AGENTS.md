# Portable working agreements

- Communicate in Traditional Chinese; keep code and commands in their original language.
- Autonomously inspect, edit and perform lightweight verification. Preserve uncommitted work; do not commit or push unless requested.
- Inspect this machine's actual hardware, permissions, filesystem and running jobs. Do not assume this is basic-pc, a shared NFS machine, or any particular GPU configuration.
- Obtain explicit approval before sudo, system-wide changes, authentication changes, new services/ports, destructive operations, or substantial compute launches. Ordinary development and lightweight checks can proceed.
- On shared machines, never interfere with other users or their processes. GPU utilization/VRAM alone does not prove availability; check process ownership and skip unknown or other-user workloads.
- For new Python projects default to uv, pyproject.toml and a project .venv; respect deliberate existing workflows. Do not install global Python libraries. Keep lockfiles consistent and avoid changing environments used by running jobs.
- Use task-appropriate bounded parallelism; prevent nested CPU oversubscription. Select workers from current CPU/RAM/I/O capacity rather than hard-coded host-specific counts.
- Use tmux or an existing persistent mechanism for long jobs; avoid duplicates and record exact commands, PID/session, working directory, logs and outputs.
- Preserve existing SSH keys, authentication, umask and unrelated configuration. Back up consequential configuration edits. Keep credentials out of logs and source control.
- Superpowers is opt-in for the current task. Do not automatically activate its skills or design approval process unless explicitly requested.
