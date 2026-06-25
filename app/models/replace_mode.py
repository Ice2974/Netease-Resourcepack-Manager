from __future__ import annotations

from enum import Enum


class ReplaceMode(Enum):
    """替换模式枚举。

    FULL: 全量替换，清空目标除 manifest.json 外的内容后复制导入包内容。
    MERGE: 覆盖合并，保留目标原有文件，导入包同名文件覆盖。
    ADD_ONLY: 仅新增，只复制目标中不存在的文件，绝不覆盖已有内容。
    """

    FULL = "full"
    MERGE = "merge"
    ADD_ONLY = "add_only"

    @property
    def display_name(self) -> str:
        return {
            ReplaceMode.FULL: "全量替换",
            ReplaceMode.MERGE: "覆盖合并",
            ReplaceMode.ADD_ONLY: "仅新增",
        }[self]
