#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

def get_process_pids(process_name: str) -> list:
    """Get PIDs for the specified process name"""
    try:
        result = subprocess.run(['pgrep', f'^{process_name}$'],
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"No process named '{process_name}' found")
            sys.exit(1)
        return result.stdout.strip().split()
    except subprocess.CalledProcessError:
        print("Error running pgrep command")
        sys.exit(1)

def get_working_dir(pid: str) -> str:
    """Get working directory for a PID"""
    try:
        result = subprocess.run(['sudo', 'pwdx', pid],
                              capture_output=True, text=True)
        return result.stdout.split(':', 1)[1].strip()
    except subprocess.CalledProcessError:
        return "N/A"

def get_socket_count(pid: str) -> int:
    """Get socket count for a PID"""
    try:
        result = subprocess.run(['sudo', 'ls', '-l', f'/proc/{pid}/fd/'],
                              capture_output=True, text=True)
        return result.stdout.count('socket')
    except subprocess.CalledProcessError:
        return 0

def get_nofile_limit(pid: str) -> str:
    """Get max open files limit for a PID"""
    try:
        with open(f'/proc/{pid}/limits', 'r') as f:
            for line in f:
                if "Max open files" in line:
                    return line.split()[3]
    except (PermissionError, FileNotFoundError):
        return "N/A"
    return "N/A"

def get_memory_usage(pid: str) -> str:
    """Get memory usage in human readable format"""
    try:
        result = subprocess.run(['sudo', 'ps', '-p', pid, '-o', 'rss='],
                              capture_output=True, text=True)
        mem_kb = int(result.stdout.strip())

        if mem_kb >= 1048576:  # 1GB = 1048576KB
            return f"{mem_kb/1048576:.2f}GB"
        elif mem_kb >= 1024:   # 1MB = 1024KB
            return f"{mem_kb/1024:.2f}MB"
        else:
            return f"{mem_kb}KB"
    except subprocess.CalledProcessError:
        return "N/A"

def main():
    if len(sys.argv) != 2:
        print("Usage: script.py <process_name>")
        sys.exit(1)

    process_name = sys.argv[1]
    pids = get_process_pids(process_name)

    # Print header
    print(f"{'PID':<10} {'FDs':<10} {'NOFILE':<12} {'MEMORY':<15} {'PATH'}")
    print(f"{'---':<10} {'---':<10} {'------':<12} {'-------':<15} {'----'}")

    # Process each PID
    for pid in pids:
        if not Path(f"/proc/{pid}").exists():
            continue

        work_dir = get_working_dir(pid)
        socket_count = get_socket_count(pid)
        nofile = get_nofile_limit(pid)
        memory = get_memory_usage(pid)

        print(f"{pid:<10} {socket_count:<10} {nofile:<12} {memory:<15} {work_dir}")

if __name__ == "__main__":
    main()