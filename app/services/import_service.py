from __future__ import annotations

from pathlib import PurePosixPath
import zipfile
from typing import Any

from app.models.operations import ValidationResult
from app.utils.manifest import extract_manifest_name, load_json_from_bytes


class ImportService:
    SUPPORTED_SUFFIXES = {".zip", ".mcpack"}

    def validate_archive(self, archive_path) -> ValidationResult:
        suffix = archive_path.suffix.lower()
        if suffix not in self.SUPPORTED_SUFFIXES:
            return ValidationResult(
                valid=False,
                message="不支持的文件格式，仅支持 .zip 和 .mcpack",
                archive_path=archive_path,
                import_name=archive_path.stem,
                root_prefix="",
            )

        try:
            with zipfile.ZipFile(archive_path, "r") as zf:
                manifest_entry = self._find_manifest_entry(zf)
                if not manifest_entry:
                    return ValidationResult(
                        valid=False,
                        message="校验失败：压缩包中未找到 manifest.json",
                        archive_path=archive_path,
                        import_name=archive_path.stem,
                        root_prefix="",
                    )

                raw = zf.read(manifest_entry)
                manifest = load_json_from_bytes(raw)
                valid, reason = self._is_bedrock_resource_manifest(manifest)
                if not valid:
                    return ValidationResult(
                        valid=False,
                        message=f"校验失败：{reason}",
                        archive_path=archive_path,
                        import_name=archive_path.stem,
                        root_prefix=str(PurePosixPath(manifest_entry).parent).strip("."),
                    )

                import_name = extract_manifest_name(manifest, archive_path.stem)
                root_prefix = str(PurePosixPath(manifest_entry).parent).strip(".")
                return ValidationResult(
                    valid=True,
                    message="校验通过：这是一个合法的 Bedrock 资源包。",
                    archive_path=archive_path,
                    import_name=import_name,
                    root_prefix=root_prefix,
                )
        except zipfile.BadZipFile:
            return ValidationResult(
                valid=False,
                message="校验失败：文件不是有效的压缩包。",
                archive_path=archive_path,
                import_name=archive_path.stem,
                root_prefix="",
            )
        except Exception as exc:  # noqa: BLE001
            return ValidationResult(
                valid=False,
                message=f"校验失败：{exc}",
                archive_path=archive_path,
                import_name=archive_path.stem,
                root_prefix="",
            )

    def _find_manifest_entry(self, zf: zipfile.ZipFile) -> str | None:
        candidates: list[str] = []
        for name in zf.namelist():
            path = PurePosixPath(name)
            if path.name.lower() == "manifest.json":
                candidates.append(name)

        if not candidates:
            return None

        candidates.sort(key=lambda item: len(PurePosixPath(item).parts))
        return candidates[0]

    def _is_bedrock_resource_manifest(self, manifest: dict[str, Any]) -> tuple[bool, str]:
        if "format_version" not in manifest:
            return False, "manifest.json 缺少 format_version"

        header = manifest.get("header")
        modules = manifest.get("modules")

        if not isinstance(header, dict):
            return False, "manifest.json 缺少 header"
        if not isinstance(modules, list) or not modules:
            return False, "manifest.json 缺少 modules"

        has_resources = False
        bedrock_like = False
        for module in modules:
            if not isinstance(module, dict):
                continue
            module_type = module.get("type")
            if module_type == "resources":
                has_resources = True
            if isinstance(module.get("uuid"), str) and module.get("version") is not None:
                bedrock_like = True

        if has_resources:
            return True, ""
        if bedrock_like:
            return True, ""
        return False, "modules 中未找到 type=resources，且结构不符合常见 Bedrock 资源包"
