from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4


class LogService:
    def __init__(self, log_dir: Path) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"run_{timestamp}.log"
        
        # Touch the file to ensure it exists before logging handler tries to open it with 'a'
        if not self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                pass

        self.logger = logging.getLogger(f"NRM.{timestamp}.{uuid4().hex}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        file_handler = logging.FileHandler(str(self.log_file), encoding="utf-8")
        file_handler.setFormatter(formatter)

        for handler in list(self.logger.handlers):
            handler.close()
            self.logger.removeHandler(handler)
        self.logger.addHandler(file_handler)

    def info(self, message: str) -> None:
        self.logger.info(message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)

    def error(self, message: str) -> None:
        self.logger.error(message)

    def exception(self, message: str) -> None:
        self.logger.exception(message)

    def close(self) -> None:
        for handler in list(self.logger.handlers):
            handler.close()
            self.logger.removeHandler(handler)
