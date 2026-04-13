from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from app.config import VERSION, ensure_data_dirs, get_packcache_dir
from app.services.backup_service import BackupService
from app.services.import_service import ImportService
from app.services.log_service import LogService
from app.services.replace_service import ReplaceService
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow
from app.utils.runtime_paths import get_resource_path


def main() -> int:
    dirs = ensure_data_dirs()
    packcache_dir = get_packcache_dir()

    log_service = LogService(dirs["logs"])
    log_service.info(f"Netease Resourcepack Manager v{VERSION} 启动")
    log_service.info(f"packcache目录: {packcache_dir}")

    scan_service = ScanService(packcache_dir)
    import_service = ImportService()
    backup_service = BackupService(dirs["backups"])
    replace_service = ReplaceService(
        backup_service=backup_service,
        import_service=import_service,
        log_service=log_service,
    )

    app = QApplication(sys.argv)
    
    qss_path = get_resource_path("app", "ui", "styles.qss")
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    window = MainWindow(
        scan_service=scan_service,
        import_service=import_service,
        replace_service=replace_service,
        log_service=log_service,
        packcache_dir=packcache_dir,
        logs_dir=dirs["logs"],
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
