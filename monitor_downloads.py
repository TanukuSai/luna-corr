"""
Live terminal monitor for the background PRADAN download task.
Usage: python monitor_downloads.py
"""
import time
import sys
from pathlib import Path

LOG_FILE = Path(r"C:\Users\saita\.gemini\antigravity-ide\brain\3c8789e3-cd50-4d51-b8d6-aa53781fa640\.system_generated\tasks\task-71.log")

def main():
    if not LOG_FILE.exists():
        print(f"Log file not found at: {LOG_FILE}")
        return

    print("=" * 60)
    print("  LUNA-CORR: Live PRADAN Bulk Download Terminal Stream")
    print("=" * 60)
    print(f"Streaming from: {LOG_FILE.name}\n(Press Ctrl+C to stop monitoring)\n")

    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        # Seek near end to start streaming recent output
        f.seek(max(0, LOG_FILE.stat().st_size - 3000))
        lines = f.read().splitlines()
        for line in lines[-20:]:
            print(line)

        try:
            while True:
                line = f.readline()
                if line:
                    print(line, end="")
                else:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[Monitoring paused. Background download is still running.]")

if __name__ == "__main__":
    main()
