#!/usr/bin/env python3
"""Gated access to PALMA II for the idp project.

All cluster access goes through this script so the standing limits in PRD
section 8 are enforced in code. It reuses the SSH connection the user opened
with `ssh palma` (or their `palma` alias) and never prompts for credentials.

Usage:
  palma.py check                 is the shared connection open?
  palma.py status                my jobs, GPU-hours used today, idle GPUs
  palma.py ro <command...>       run a read-only command (allowlisted)
  palma.py submit <script> [KEY=VALUE ...] [--dry-run]
                                 validate limits, copy script, sbatch
  palma.py logs <jobid> [-n N]   state plus tail of the job's output
  palma.py cancel <jobid>        scancel, only for idp-* jobs of this user
  palma.py put <local> <remote-relative-path>
  palma.py get <remote-relative-path> <local>
  palma.py sync                  copy the committed code to code/<sha>/ (immutable)
"""
from __future__ import annotations

import datetime as dt
import re
import shlex
import subprocess
import sys
from pathlib import Path

HOST = "palma"
PROJECT = "/scratch/tmp/$USER/idp"  # expanded remotely
JOB_PREFIX = "idp-"

# Standing limits, PRD section 8 (set by the user on 2026-11-19).
MAX_GPUS_AT_ONCE = 2
MAX_HOURS_PER_JOB = 4.0
MAX_GPU_HOURS_PER_DAY = 30.0

# First word of commands that only read state.
READ_ONLY = {
    "sinfo", "squeue", "sacct", "sshare", "sprio", "scontrol", "sacctmgr",
    "myquota", "ls", "cat", "head", "tail", "wc", "du", "df", "stat", "find",
    "grep", "module", "hostname", "date", "nvidia-smi", "seff", "file",
}
# Substrings that turn an allowlisted command into a write.
FORBIDDEN = (">", "|", ";", "&", "`", "$(", " update", " create", " delete",
             " modify", " add ", "-delete", "-exec", " requeue", " hold",
             " release", " suspend", " resume", " reconfigure")
NOISE = ("post-quantum", "store now, decrypt later", "server may need to be upgraded")


def die(msg: str) -> "None":
    print(f"palma: {msg}", file=sys.stderr)
    sys.exit(1)


def ssh(remote: str, check: bool = True, stdin: str | None = None) -> str:
    """Run a command on the login node in a login shell (needed for `module`)."""
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ControlMaster=no", HOST,
           "bash -lc " + shlex.quote(remote)]
    p = subprocess.run(cmd, capture_output=True, text=True, input=stdin)
    out = "\n".join(l for l in (p.stdout + p.stderr).splitlines()
                    if not any(n in l for n in NOISE))
    if check and p.returncode != 0:
        die(f"remote command failed ({p.returncode}):\n{out}")
    return out


def connected() -> bool:
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-O", "check", HOST],
                       capture_output=True, text=True)
    return p.returncode == 0


def require_connection() -> None:
    if not connected():
        die("no shared connection. Ask the user to run `palma` (or `ssh palma`) "
            "in their own terminal and keep it open. Do not try to authenticate.")


# ---------------------------------------------------------------- parsing

def parse_time(s: str) -> float:
    """Slurm time string to hours."""
    days = 0
    if "-" in s:
        d, s = s.split("-", 1)
        days = int(d)
    parts = [int(x) for x in s.split(":")]
    if days or len(parts) == 3:
        parts = parts + [0] * (3 - len(parts))  # D-HH[:MM[:SS]]
        h, m, sec = parts[0], parts[1], parts[2]
    elif len(parts) == 2:                       # MM:SS
        h, m, sec = 0, parts[0], parts[1]
    else:                                       # MM
        h, m, sec = 0, parts[0], 0
    return days * 24 + h + m / 60 + sec / 3600


def gpus_in(text: str) -> int:
    """GPU count from a gres/tres string such as gpu:rtx4090:2 or gres/gpu=2."""
    m = re.search(r"gres/gpu=(\d+)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"gpu(?::[A-Za-z0-9_.]+)?:(\d+)", text)
    if m:
        return int(m.group(1))
    return 1 if re.search(r"\bgpu\b", text) else 0


def sbatch_options(script: str) -> dict[str, str]:
    opts: dict[str, str] = {}
    last = ""
    short = {"J": "job-name", "t": "time", "p": "partition", "a": "array",
             "G": "gpus", "o": "output", "e": "error", "N": "nodes"}
    for line in script.splitlines():
        if not line.startswith("#SBATCH"):
            if line.strip() and not line.startswith("#"):
                break  # directives end at the first command
            continue
        for tok in shlex.split(line[len("#SBATCH"):]):
            if tok.startswith("--"):
                k, _, v = tok[2:].partition("=")
                opts[k] = v
                last = k
            elif tok.startswith("-") and len(tok) >= 2 and tok[1] in short:
                last = short[tok[1]]
                opts[last] = tok[2:]
            else:
                opts[last] = tok  # value given as a separate token
    return opts


def array_shape(spec: str) -> tuple[int, int]:
    """(number of tasks, max running at once) for an --array spec."""
    throttle = None
    if "%" in spec:
        spec, t = spec.split("%", 1)
        throttle = int(t)
    n = 0
    for part in spec.split(","):
        m = re.fullmatch(r"(\d+)(?:-(\d+)(?::(\d+))?)?", part)
        if not m:
            die(f"cannot parse --array={spec}")
        lo, hi, step = int(m.group(1)), int(m.group(2) or m.group(1)), int(m.group(3) or 1)
        n += len(range(lo, hi + 1, step))
    return n, min(throttle or n, n)


# ---------------------------------------------------------------- accounting

def active_gpus() -> int:
    """GPUs held or requested by this project's running and pending jobs."""
    out = ssh("squeue -h -u $USER -o '%i|%j|%T|%b'")
    total = 0
    for line in out.splitlines():
        if line.count("|") != 3:
            continue
        jobid, name, state, gres = line.split("|")
        if not name.startswith(JOB_PREFIX):
            continue
        g = gpus_in(gres)
        m = re.search(r"\[(.+)\]", jobid)  # pending part of an array
        if m and state == "PENDING":
            _, conc = array_shape(m.group(1))
            g *= conc
        total += g
    return total


def gpu_hours_today() -> float:
    """Worst case: elapsed for finished jobs, full time limit for active ones."""
    today = dt.date.today().isoformat()
    out = ssh(f"sacct -u $USER -S {today}T00:00:00 -X -n -P "
              "-o jobname,state,elapsedraw,timelimitraw,alloctres,reqtres")
    hours = 0.0
    for line in out.splitlines():
        f = line.split("|")
        if len(f) != 6 or not f[0].startswith(JOB_PREFIX):
            continue
        name, state, elapsed, limit, alloc, req = f
        g = gpus_in(alloc) or gpus_in(req)
        if not g:
            continue
        if state.split()[0] in ("RUNNING", "PENDING", "REQUEUED", "SUSPENDED"):
            h = (int(limit) / 60) if limit.isdigit() else MAX_HOURS_PER_JOB
        else:
            h = int(elapsed or 0) / 3600
        hours += g * h
    return hours


# ---------------------------------------------------------------- commands

def cmd_check() -> None:
    print("connected" if connected() else "not connected")
    sys.exit(0 if connected() else 1)


def cmd_status() -> None:
    require_connection()
    print(ssh("squeue -u $USER -o '%.12i %.24j %.9T %.10M %.10l %.14b %R'"))
    print(f"\nGPU-hours today (worst case): {gpu_hours_today():.1f} / {MAX_GPU_HOURS_PER_DAY:.0f}")
    print(f"GPUs active or queued: {active_gpus()} / {MAX_GPUS_AT_ONCE}")
    print("\nGPU nodes with free capacity (partition node state gres cpus A/I/O/T):")
    print(ssh("sinfo -N -h -t idle,mix -o '%P %N %t %G %C' "
              "-p gpuexpress-zen4,gpu4090,gpua100,gpuh200,gpuh200mini,requeue-gpu"))


def cmd_ro(args: list[str]) -> None:
    require_connection()
    if not args:
        die("ro needs a command")
    line = shlex.join(args)  # keeps quoting; use --me instead of $USER
    if args[0].split("/")[-1] not in READ_ONLY:
        die(f"'{args[0]}' is not on the read-only allowlist: {sorted(READ_ONLY)}")
    low = " " + line.lower() + " "
    bad = [x for x in FORBIDDEN if x in low]
    if bad:
        die(f"refused, looks like a write or a compound command: {bad}")
    print(ssh(line, check=False))


def cmd_submit(args: list[str]) -> None:
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    env = [a for a in args[1:] if re.fullmatch(r"[A-Z][A-Z0-9_]*=[\w.:/=@\- ]*", a)]
    if not args or len(env) != len(args) - 1:
        die("usage: submit <script> [KEY=VALUE ...] [--dry-run]  (values: letters, digits, . : / = - space)")
    args = args[:1]
    path = Path(args[0])
    script = path.read_text()
    o = sbatch_options(script)

    problems = []
    name = o.get("job-name", "")
    if not name.startswith(JOB_PREFIX):
        problems.append(f"--job-name must start with '{JOB_PREFIX}' (got '{name}')")
    if "time" not in o:
        problems.append("--time is required")
    elif parse_time(o["time"]) > MAX_HOURS_PER_JOB:
        problems.append(f"--time {o['time']} exceeds {MAX_HOURS_PER_JOB:g} h per job")
    if "partition" not in o:
        problems.append("--partition is required")
    if any(k in o for k in ("gpus-per-task", "gpus-per-node", "ntasks-per-gpu")):
        problems.append("use --gres=gpu:N or --gpus=N so the GPU count can be checked")
    if int(o.get("nodes", "1").split("-")[-1] or 1) > 1:
        problems.append("multi-node jobs need the user's approval")

    gpus = gpus_in(o.get("gres", "")) or (gpus_in("gres/gpu=" + o["gpus"].split(":")[-1])
                                         if "gpus" in o else 0)
    tasks, conc = array_shape(o["array"]) if "array" in o else (1, 1)
    hours = parse_time(o["time"]) if "time" in o and not problems else 0.0

    if not problems and gpus:
        require_connection()
        act, used = active_gpus(), gpu_hours_today()
        if act + gpus * conc > MAX_GPUS_AT_ONCE:
            problems.append(f"would hold {act} + {gpus * conc} GPUs at once, "
                            f"limit {MAX_GPUS_AT_ONCE} (add an array throttle such as %2)")
        need = gpus * tasks * hours
        if used + need > MAX_GPU_HOURS_PER_DAY:
            problems.append(f"worst case {need:.1f} GPU-h on top of {used:.1f} today "
                            f"exceeds {MAX_GPU_HOURS_PER_DAY:g}")
    if problems:
        die("submission refused; ask the user before going beyond these limits:\n  - "
            + "\n  - ".join(problems))

    summary = (f"{name}: partition={o['partition']} gpus={gpus} tasks={tasks} "
               f"concurrent={conc} time={o['time']}")
    if dry:
        print("dry run OK  " + summary)
        return
    require_connection()
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    remote = f"{PROJECT}/jobs/{stamp}-{path.name}"
    ssh(f"umask 077; mkdir -p {PROJECT}/jobs {PROJECT}/logs; cat > {remote}", stdin=script)
    out_flag = "" if "output" in o else f"-o {PROJECT}/logs/%x-%A_%a.out " if "array" in o \
        else f"-o {PROJECT}/logs/%x-%j.out "
    export = ("--export=" + shlex.quote(",".join(["ALL"] + env)) + " ") if env else ""
    jobid = ssh(f"cd {PROJECT} && sbatch --parsable {export}{out_flag}{remote}").strip().splitlines()[-1]
    print(f"submitted {jobid}  {summary}\nscript: {remote}")


def cmd_logs(args: list[str]) -> None:
    require_connection()
    if not args or not re.fullmatch(r"\d+(_\d+)?", args[0]):
        die("usage: logs <jobid> [-n N]")
    n = int(args[2]) if len(args) == 3 and args[1] == "-n" else 60
    jid = args[0]
    print(ssh(f"sacct -j {jid} -X -o jobid,jobname%24,state,elapsed,exitcode,nodelist"))
    print(ssh(f"f=$(scontrol show job {jid} 2>/dev/null | grep -oP 'StdOut=\\K\\S+' | head -1); "
              f"[ -z \"$f\" ] && f=$(ls -t {PROJECT}/logs/*{jid}*.out 2>/dev/null | head -1); "
              f"echo \"--- $f\"; tail -n {n} \"$f\"", check=False))


def cmd_cancel(args: list[str]) -> None:
    require_connection()
    if len(args) != 1 or not re.fullmatch(r"\d+(_\d+)?", args[0]):
        die("usage: cancel <jobid>")
    info = ssh(f"squeue -h -j {args[0]} -u $USER -o '%j'", check=False).splitlines()
    if not info or not all(n.startswith(JOB_PREFIX) for n in info):
        die(f"job {args[0]} is not an active {JOB_PREFIX}* job of this user; not cancelling")
    ssh(f"scancel {args[0]}")
    print(f"cancelled {args[0]}")


def safe_rel(p: str) -> str:
    if p.startswith("/") or ".." in Path(p).parts:
        die("remote path must be relative to the project directory, without '..'")
    return p


def cmd_put(args: list[str]) -> None:
    require_connection()
    if len(args) != 2:
        die("usage: put <local> <remote-relative-path>")
    rel = safe_rel(args[1])
    exists = ssh(f"[ -e {PROJECT}/{rel} ] && echo yes || echo no").strip()
    if exists == "yes":
        die(f"{rel} already exists on PALMA; overwriting needs the user's OK")
    data = Path(args[0]).read_bytes()
    cmd = ["ssh", "-o", "BatchMode=yes", HOST,
           f"umask 077; mkdir -p $(dirname {PROJECT}/{rel}) && cat > {PROJECT}/{rel}"]
    subprocess.run(cmd, input=data, check=True, stderr=subprocess.DEVNULL)
    print(f"wrote {rel} ({len(data)} bytes)")


def cmd_get(args: list[str]) -> None:
    require_connection()
    if len(args) != 2:
        die("usage: get <remote-relative-path> <local>")
    rel = safe_rel(args[0])
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", HOST, f"cat {PROJECT}/{rel}"],
                       capture_output=True)
    if p.returncode != 0:
        die(f"cannot read {rel}")
    Path(args[1]).write_bytes(p.stdout)
    print(f"saved {args[1]} ({len(p.stdout)} bytes)")


def cmd_sync() -> None:
    """Snapshot HEAD to code/<short sha>/ on PALMA. Jobs run from a snapshot,
    so every result maps to one commit and running jobs never see code change."""
    require_connection()
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                          text=True, check=True).stdout.strip()
    if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True,
                      cwd=root).stdout.strip():
        die("uncommitted changes; commit first so the snapshot matches a commit")
    sha = subprocess.run(["git", "rev-parse", "--short=10", "HEAD"], capture_output=True,
                         text=True, check=True, cwd=root).stdout.strip()
    dest = f"{PROJECT}/code/{sha}"
    if ssh(f"[ -e {dest} ] && echo yes || echo no").strip() == "yes":
        print(f"code/{sha} already on PALMA")
        return
    tar = subprocess.run(["git", "archive", "--format=tar", "HEAD"], capture_output=True,
                         check=True, cwd=root).stdout
    cmd = ["ssh", "-o", "BatchMode=yes", HOST,
           f"umask 077; mkdir -p {dest}.tmp && tar -x -C {dest}.tmp && mv {dest}.tmp {dest}"]
    subprocess.run(cmd, input=tar, check=True, stderr=subprocess.DEVNULL)
    print(f"synced code/{sha} ({len(tar) // 1024} KiB)")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, args = sys.argv[1], sys.argv[2:]
    table = {"check": lambda: cmd_check(), "status": lambda: cmd_status(),
             "ro": lambda: cmd_ro(args), "submit": lambda: cmd_submit(args),
             "logs": lambda: cmd_logs(args), "cancel": lambda: cmd_cancel(args),
             "put": lambda: cmd_put(args), "get": lambda: cmd_get(args), "sync": lambda: cmd_sync()}
    if cmd not in table:
        die(f"unknown command '{cmd}'\n{__doc__}")
    table[cmd]()


if __name__ == "__main__":
    main()
