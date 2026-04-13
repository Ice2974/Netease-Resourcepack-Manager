from __future__ import annotations

from pathlib import Path, PurePosixPath
import shutil
import zipfile

from app.models.operations import ReplaceResult, RollbackResult, ValidationResult
from app.models.resource_pack import ResourcePack
from app.services.backup_service import BackupService
from app.services.import_service import ImportService
from app.services.log_service import LogService


class ReplaceService:
    def __init__(
        self,
        backup_service: BackupService,
        import_service: ImportService,
        log_service: LogService,
    ) -> None:
        self.backup_service = backup_service
        self.import_service = import_service
        self.log_service = log_service

    def replace_from_archive(self, target_pack: ResourcePack, validation: ValidationResult) -> ReplaceResult:
        target_name = target_pack.display_name
        import_name = validation.import_name
        backup_path: Path | None = None

        try:
            self.log_service.info(f"替换开始: target={target_pack.path}, import={validation.archive_path}")
            backup_path = self.backup_service.create_backup(target_pack.path, target_pack.folder_name)
            self.log_service.info(f"备份创建成功: {backup_path}")

            self._clear_target_except_manifest(target_pack.path)
            self._copy_archive_content(target_pack.path, validation)

            self.log_service.info("替换成功")
            return ReplaceResult(
                success=True,
                message=f"已将[{target_name}]替换为[{import_name}]，请重新进入服务器使材质生效。",
                target_name=target_name,
                import_name=import_name,
                backup_path=backup_path,
            )
        except Exception as exc:  # noqa: BLE001
            error_text = str(exc)
            self.log_service.error(f"替换失败原因: {error_text}")
            if "used by another process" in error_text.lower() or "being used" in error_text.lower() or "权限" in error_text:
                error_text = f"{error_text}。请先关闭Minecraft进程后重试。"

            rollback_msg = ""
            if backup_path is not None:
                self.log_service.info("回滚开始")
                try:
                    self.backup_service.restore_backup(backup_path, target_pack.path)
                    self.log_service.info("回滚成功")
                except Exception as rollback_exc:  # noqa: BLE001
                    rollback_msg = f" 回滚失败: {rollback_exc}"
                    self.log_service.error(f"回滚失败原因: {rollback_exc}")
            return ReplaceResult(
                success=False,
                message=f"替换失败：{error_text}{rollback_msg}",
                target_name=target_name,
                import_name=import_name,
                backup_path=backup_path,
                error=error_text,
            )

    def rollback_latest(self, target_pack: ResourcePack) -> RollbackResult:
        backup_path = self.backup_service.find_latest_backup(target_pack.folder_name)
        if not backup_path:
            return RollbackResult(success=False, message="未找到可用备份，无法回滚。", backup_path=None)

        self.log_service.info("回滚开始")
        try:
            self.backup_service.restore_backup(backup_path, target_pack.path)
            self.log_service.info("回滚成功")
            return RollbackResult(success=True, message="已回滚到最近一次替换前状态。", backup_path=backup_path)
        except Exception as exc:  # noqa: BLE001
            self.log_service.error(f"回滚失败原因: {exc}")
            return RollbackResult(
                success=False,
                message=f"回滚失败：{exc}",
                backup_path=backup_path,
                error=str(exc),
            )

    def _clear_target_except_manifest(self, target_dir: Path) -> None:
        for child in target_dir.iterdir():
            if child.name.lower() == "manifest.json":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()

    def _copy_archive_content(self, target_dir: Path, validation: ValidationResult) -> None:
        root_prefix = validation.root_prefix.replace("\\", "/").strip("/")
        prefix_parts = tuple(PurePosixPath(root_prefix).parts) if root_prefix else tuple()

        with zipfile.ZipFile(validation.archive_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue

                src_path = PurePosixPath(info.filename)
                parts = src_path.parts
                if prefix_parts:
                    if parts[: len(prefix_parts)] != prefix_parts:
                        continue
                    rel_parts = parts[len(prefix_parts) :]
                else:
                    rel_parts = parts

                if not rel_parts:
                    continue

                rel_path = Path(*rel_parts)
                if rel_path.name.lower() == "manifest.json" and len(rel_path.parts) == 1:
                    continue

                safe_target = (target_dir / rel_path).resolve()
                target_root = target_dir.resolve()
                if target_root not in safe_target.parents and safe_target != target_root:
                    raise ValueError("压缩包包含不安全路径，已拦截。")

                safe_target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, safe_target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
