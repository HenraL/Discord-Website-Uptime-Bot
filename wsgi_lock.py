import os
import time
import threading
from pathlib import Path

LOCKFILE = Path(__file__).parent / "discord_bot_wsgi.lock"
MAX_AGE_SECONDS = 600  # 10 minutes


def is_pid_alive(pid: int) -> bool:
    """
    Check whether a given process ID is currently running.

    Args:
        pid (int): The process ID to check.

    Returns:
        bool: True if the process exists and is accessible, False otherwise.
    """
    if pid <= 0:
        # Invalid PID, cannot be a real user process
        return False
    try:
        # Signal 0 does not kill the process; it only checks if it's alive
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False
    return True


def acquire_lockfile() -> bool:
    """
    Attempt to atomically acquire lock. Return True if bot should start.
    """
    try:
        # Attempt atomic creation
        fd = os.open(LOCKFILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, 'w') as f:
            f.write(f"{os.getpid()}\n{time.time()}")
        return True
    except FileExistsError:
        # Lockfile exists, check if stale
        try:
            with open(LOCKFILE, 'r', encoding="utf-8", newline="\n") as f:
                content = f.read().splitlines()
                if len(content) != 2:
                    return False
                pid, ts = int(content[0]), float(content[1])
        except Exception:
            return False

        if (time.time() - ts) > MAX_AGE_SECONDS or not is_pid_alive(pid):
            # Stale lock, remove and retry
            try:
                LOCKFILE.unlink()
                return acquire_lockfile()
            except Exception:
                return False
        return False


def refresh_lockfile_thread():
    """Daemon thread to refresh the lockfile timestamp."""
    def refresh_loop():
        while True:
            time.sleep(60)
            try:
                if LOCKFILE.exists():
                    pid, _ = open(
                        LOCKFILE,
                        "r",
                        encoding="utf-8",
                        newline="\n"
                    ).read().splitlines()
                    if int(pid) == os.getpid():
                        with open(
                            LOCKFILE,
                            'w',
                            encoding="utf-8",
                            newline="\n"
                        ) as f:
                            f.write(f"{pid}\n{time.time()}")
            except Exception as e:
                print(
                    f"[Lock Refresh] Failed to update lockfile: {e}", flush=True)

    t = threading.Thread(target=refresh_loop, daemon=True)
    t.start()


def acquire_wsgi_lock() -> bool:
    """Main entry to acquire WSGI lock."""
    if acquire_lockfile():
        refresh_lockfile_thread()
        return True
    print("[WSGI Lock] Another instance is running or lock is valid, aborting startup.", flush=True)
    return False
