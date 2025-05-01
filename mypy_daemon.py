#!/usr/bin/env python
"""
Script for managing mypy daemon.
Usage:
    python mypy_daemon.py start - start mypy daemon
    python mypy_daemon.py stop - stop mypy daemon
    python mypy_daemon.py restart - restart mypy daemon
    python mypy_daemon.py check - check files with mypy daemon
"""

import sys
import subprocess
import os


def get_base_dir():
    return os.path.dirname(os.path.abspath(__file__))


def run_command(cmd, **kwargs):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    print(f"Exit code: {result.returncode}")
    return result.returncode


def start_daemon():
    base_dir = get_base_dir()
    config_path = os.path.join(base_dir, "mypy.ini")
    src_path = os.path.join(base_dir, "src")
    
    cmd = [sys.executable, "-m", "mypy.dmypy", "start", "--", f"--config-file={config_path}"]
    return run_command(cmd)


def stop_daemon():
    cmd = [sys.executable, "-m", "mypy.dmypy", "stop"]
    return run_command(cmd)


def restart_daemon():
    stop_daemon()
    return start_daemon()


def check_files():
    base_dir = get_base_dir()
    src_path = os.path.join(base_dir, "src")
    
    cmd = [sys.executable, "-m", "mypy.dmypy", "check", src_path]
    return run_command(cmd)


def status_daemon():
    cmd = [sys.executable, "-m", "mypy.dmypy", "status"]
    return run_command(cmd)


def main():
    if len(sys.argv) < 2:
        print("Usage: python mypy_daemon.py [start|stop|restart|check|status]")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "start":
        return start_daemon()
    elif command == "stop":
        return stop_daemon()
    elif command == "restart":
        return restart_daemon()
    elif command == "check":
        return check_files()
    elif command == "status":
        return status_daemon()
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
