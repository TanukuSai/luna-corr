"""
Live terminal monitor for the background sequential extract-and-delete task.
Usage: python monitor_unpack.py
"""
import time
import sys
from pathlib import Path

LOG_FILE = Path(r"C:\Users\saita\.gemini\antigravity-ide\brain\3c8789e3-cd50-4d51-b8d6-aa53781fa640\.system_generated\tasks\task-304.log")

def main():
    if not LOG_FILE.exists():
        print(f"Log file not found at: {LOG_FILE}")
        return

    print("=" * 65)
    print("  LUNA-CORR: Live Sequential Unpack & Storage Reclamation Monitor")
    print("=" * 65)
    print(f"Streaming from: {LOG_FILE.name}\n(Press Ctrl+C to stop viewing at any time)\n")

    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        # Seek near end to start streaming recent lines
        f.seek(max(0, LOG_FILE.stat().st_size - 2500))
        recent_lines = f.read().splitlines()
        for line in recent_lines[-15:]:
            print(line)

        try:
            while True:
                line = f.readline()
                if line:
                    print(line, end="")
                else:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\n[Monitoring paused. Background extraction is still running safely.]")

if __name__ == "__main__":
    main()
