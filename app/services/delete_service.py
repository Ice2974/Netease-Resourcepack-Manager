from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path

from app.models.operations import DeleteResult
from app.models.resource_pack import ResourcePack
from app.services.log_service import LogService


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", wintypes.WORD),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", wintypes.LPVOID),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


class DeleteService:
    def __init__(self, packcache_dir: Path, log_service: LogService) -> None:
        self.packcache_dir = packcache_dir
        self.log_service = log_service

    def delete_pack(self, target_pack: ResourcePack) -> DeleteResult:
        if not target_pack:
            return DeleteResult(success=False, message="无效的资源包", target_path=None, error="Target pack is None")

        try:
            target_path = target_pack.path

            # 安全校验
            self._validate_safe_path(target_path)

            self.log_service.info(f"尝试将资源包移入回收站: {target_path}")
            self._send_to_recycle_bin(target_path)

            if target_path.exists():
                raise RuntimeError("API调用虽未报错，但目标文件仍然存在，删除失败。")

            self.log_service.info(f"资源包移入回收站成功: {target_path}")
            return DeleteResult(
                success=True,
                message=f"已成功将资源包 [{target_pack.display_name}] 移入回收站。",
                target_path=target_path,
            )
        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)
            self.log_service.error(f"删除失败: {error_msg}")
            return DeleteResult(
                success=False,
                message=f"删除失败：{error_msg}",
                target_path=target_pack.path if target_pack else None,
                error=error_msg,
            )

    def _validate_safe_path(self, target_path: Path) -> None:
        if not target_path or not str(target_path).strip() or target_path == Path("."):
            raise ValueError("传入了空路径。")

        try:
            resolved_target = target_path.resolve(strict=True)
            resolved_cache = self.packcache_dir.resolve(strict=True)
        except FileNotFoundError:
            raise ValueError(f"路径不存在: {target_path}")

        if not resolved_target.is_dir():
            raise ValueError("目标不是一个文件夹。")

        if resolved_target == resolved_cache:
            raise ValueError("禁止删除 packcache 根目录。")

        if resolved_cache not in resolved_target.parents:
            raise ValueError("目标路径必须在 packcache 目录下。")

        if resolved_target.parent != resolved_cache:
            raise ValueError("只允许删除 packcache 的一级子目录。")

        if target_path.is_symlink() or getattr(target_path, "is_junction", lambda: False)():
            raise ValueError("目标是符号链接或软链接，拒绝删除。")

    def _send_to_recycle_bin(self, target_path: Path) -> None:
        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004
        FOF_NOERRORUI = 0x0400

        flags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI

        # SHFileOperation requires double null-terminated string
        path_str = str(target_path.resolve()) + "\0\0"

        file_op = SHFILEOPSTRUCTW()
        file_op.hwnd = None
        file_op.wFunc = FO_DELETE
        file_op.pFrom = path_str
        file_op.pTo = None
        file_op.fFlags = flags
        file_op.fAnyOperationsAborted = False
        file_op.hNameMappings = None
        file_op.lpszProgressTitle = None

        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(file_op))
        if result != 0:
            raise RuntimeError(f"系统 API 返回非零结果，可能文件被占用或无权限。错误码：{result}")
        if file_op.fAnyOperationsAborted:
            raise RuntimeError("操作被系统或用户中止。")
