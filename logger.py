import datetime
import os
from threading import Lock


class SessionLogger:
    """
    Handles logging of source transcription and target translations to a file.
    Automatically creates a file named 'logs/Lecture_%Y%m%d_%H%M%S.txt' on startup.
    Thread-safe and supports freezing when paused.
    """

    def __init__(self):
        self.lock = Lock()
        self.is_paused = False

        # Ensure logs directory exists in the workspace
        os.makedirs("logs", exist_ok=True)

        # Create log filename using format Lecture_%Y%m%d_%H%M%S.txt
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        self.filename = os.path.join("logs", f"Lecture_{timestamp_str}.txt")

        # Write initial session header
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write(f"=== Session Started at {now.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        except Exception as e:
            print(f"Failed to initialize log file: {e}")

    def set_paused(self, paused: bool):
        """Set the paused state to control logging activity."""
        with self.lock:
            self.is_paused = paused

    def log(self, src_text: str, trg1_text: str = "", trg2_text: str = ""):
        """
        Write a log entry with [HH:MM:SS] timestamp and translations.
        Does nothing if logging is currently paused.
        """
        with self.lock:
            if self.is_paused:
                return

            # Avoid logging completely empty transcriptions
            if not src_text.strip():
                return

            now = datetime.datetime.now()
            time_str = now.strftime("[%H:%M:%S]")

            try:
                with open(self.filename, "a", encoding="utf-8") as f:
                    f.write(f"{time_str}\n")
                    f.write(f"[SRC]: {src_text.strip()}\n")

                    if trg1_text and trg1_text.strip():
                        f.write(f"[TRG1]: {trg1_text.strip()}\n")

                    if trg2_text and trg2_text.strip():
                        f.write(f"[TRG2]: {trg2_text.strip()}\n")

                    f.write("-" * 40 + "\n")
            except Exception as e:
                print(f"Failed writing to log file {self.filename}: {e}")
