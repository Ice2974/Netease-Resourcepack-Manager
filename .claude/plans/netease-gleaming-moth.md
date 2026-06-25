# 适配 Windows 默认应用模式（深色 / 浅色主题）

## Context（背景）

当前 `app/ui/styles.qss` 是纯浅色主题，`app/main.py:42-44` 启动时无差别加载它，软件始终为浅色，与系统暗色模式不协调。

项目此前曾实现过主题功能（`app/utils/__pycache__/theme.cpython-313.pyc`、`tests/__pycache__/test_theme.cpython-313.pyc` 残留；`release/.../app/ui/` 下存在完整的 `styles_light.qss` 与 `styles_dark.qss` 构建产物），但源码层的 `theme.py` / `test_theme.py` 已被删除，`main.py` 也回退为只加载 `styles.qss`。本次任务是重建该能力并保证深色模式真正可用。

核心难点：样式并非全部集中在 QSS。资源包列表卡片由 `PackTableDelegate.paint()` 自绘（选中/hover/文字/文件夹与删除图标背景全是硬编码浅色 `QColor`），`drop_zone.py` 拖拽区是内联 `setStyleSheet`，状态标签（成功/错误/提示）也是内联颜色。仅切换全局 QSS 时，深色模式下这些卡片仍为白底、文字仍为深色，视觉割裂严重。因此本次按「完整适配」范围执行：让自绘元素、内联样式都按主题取色。

目标：启动时读取 Windows「选择默认应用模式」，亮→浅色、暗→深色，全界面一致。不新增 UI 设置项、不新增依赖、不引入联网、不动业务逻辑。

## 1. 问题理解

- Windows 默认应用模式存于注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize`，`AppsUseLightTheme`（DWORD）：`1`=亮、`0`=暗、键缺失=按亮色处理。
- 用 Python 标准库 `winreg` 读取，无需新增依赖（`requirements.txt` 仅 `PySide6`，保持不变）。
- `winreg` 仅 Windows 可用，需 `try/except ImportError` 回退浅色，保证非 Windows 环境（含 CI 测试）可运行。
- 主题在启动时判定一次即可；运行中切换系统主题后自动刷新成本较高，列为后续项（见第 8 节）。
- 全局 QSS + 自绘元素 + 内联样式三处都需感知主题，否则深色不完整。

## 2. 已读文件

- `app/main.py`（61 行，QSS 加载在 42-44）
- `app/config.py`（49 行，路径与数据目录，不涉及主题）
- `app/ui/styles.qss`（238 行，纯浅色）
- `app/ui/drop_zone.py`（99 行，内联 QSS 在 17-27 / 55-61 / 67-77 / 81-91，标签颜色 32 / 36）
- `app/ui/main_window.py`（`PackTableDelegate.paint()` 在 52-124，硬编码 `QColor` 集中在 61-70 / 92 / 100 / 104 / 114 / 118；folder/trash 图标创建 154-189 用 `#4B5563`/`#DC2626`；状态标签内联 `setStyleSheet` 在 336 / 358 / 367 / 401 / 411 / 727 / 765 / 768 / 781 / 786 / 797 / 801）
- `app/utils/runtime_paths.py`（`get_resource_path` 在 17-18，兼容源码与 PyInstaller）
- `NeteaseResourcepackManager.spec`（datas 在 14-16，当前打包 `styles.qss` 与 `icon.ico`）
- `release/NeteaseResourcepackManager/_internal/app/ui/styles_dark.qss`（242 行，完整深色主题，可作为新建源文件的直接参考）
- `requirements.txt`（仅 `PySide6>=6.8.0`）

## 3. 当前样式实现

- 入口：`app/main.py` 第 42-44 行，`get_resource_path("app","ui","styles.qss")` → `app.setStyleSheet(...)`，文件不存在则静默跳过。
- 全局 QSS：`app/ui/styles.qss` 纯浅色（背景 `#F3F4F6`/`#FFFFFF`，文字 `#111827`/`#374151`，主色 `#2563EB`）。
- 内联样式（深色下会不一致，本次需纳入主题）：
  - `drop_zone.py`：拖拽区背景/虚线边框普通态、hover 态、拖入高亮态，及两行标签颜色。
  - `main_window.py` `PackTableDelegate.paint()`：列表卡片选中态（`#BFDBFE`/`#EFF6FF`）、hover 态（`#E5E7EB`/`#F9FAFB`）、默认态（`#E5E7EB`/`#FFFFFF`）、卡片标题文字（`#111827`）、文件夹/删除图标 hover/选中背景、图标线稿颜色。
  - `main_window.py` 状态标签：成功 `#059669`、错误 `#DC2626`、提示 `#6B7280`/`#9CA3AF`、标题 `#111827` 等，全部内联 `setStyleSheet`。

## 4. 推荐方案

### 4.1 新增 `app/utils/theme.py`（主题判定 + 调色板）

职责单一：读注册表判定主题，提供两套颜色常量与取色函数。不依赖 Qt，纯标准库，便于单测。

```python
# 伪代码骨架
import winreg  # try/except ImportError → 仅 Windows
from __future__ import annotations

LIGHT = {
    "card_bg": "#FFFFFF", "card_border": "#E5E7EB",
    "card_selected_pen": "#BFDBFE", "card_selected_bg": "#EFF6FF",
    "card_hover_pen": "#E5E7EB", "card_hover_bg": "#F9FAFB",
    "card_text": "#111827",
    "folder_icon": "#4B5563", "folder_bg_selected": "#DBEAFE", "folder_bg_hover": "#F3F4F6",
    "trash_icon": "#DC2626", "trash_bg_selected": "#FEE2E2", "trash_bg_hover": "#FEF2F2",
    "dz_bg": "#F9FAFB", "dz_border": "#D1D5DB", "dz_hover_bg": "#F3F4F6", "dz_hover_border": "#9CA3AF",
    "dz_active_bg": "#EFF6FF", "dz_active_border": "#3B82F6",
    "dz_label": "#6B7280", "dz_sublabel": "#9CA3AF",
    "success": "#059669", "error": "#DC2626", "hint": "#6B7280",
    "title_text": "#111827", "file_text": "#4B5563",
}
DARK = {
    "card_bg": "#2B2B2B", "card_border": "#3A3A3A",
    "card_selected_pen": "#1E3A5F", "card_selected_bg": "#1E3A5F",
    "card_hover_pen": "#3A3A3A", "card_hover_bg": "#333333",
    "card_text": "#E5E7EB",
    "folder_icon": "#9CA3AF", "folder_bg_selected": "#1E3A5F", "folder_bg_hover": "#333333",
    "trash_icon": "#F87171", "trash_bg_selected": "#3A1F1F", "trash_bg_hover": "#3A1F1F",
    "dz_bg": "#2B2B2B", "dz_border": "#3A3A3A", "dz_hover_bg": "#333333", "dz_hover_border": "#4B5563",
    "dz_active_bg": "#1E3A5F", "dz_active_border": "#3B82F6",
    "dz_label": "#9CA3AF", "dz_sublabel": "#6B7280",
    "success": "#34D399", "error": "#F87171", "hint": "#9CA3AF",
    "title_text": "#E5E7EB", "file_text": "#9CA3AF",
}

def get_theme() -> str:
    # winreg 打开 HKCU\...\Themes\Personalize 读 AppsUseLightTheme
    # 异常 / 键缺失 / 非 Windows → "light"
    ...

def palette() -> dict:
    return DARK if get_theme() == "dark" else LIGHT
```

颜色取值对齐 `release/.../styles_dark.qss` 与现有 `styles.qss`，保证 QSS 与自绘元素配色统一。深色 success/error 用更亮的 `#34D399`/`#F87171`（与 `styles_dark.qss` 中 `SuccessLabel`/`ErrorLabel` 一致）。

### 4.2 QSS 文件：采用对称命名

- 新建 `app/ui/styles_light.qss`：内容 = 现有 `app/ui/styles.qss`（浅色，原样迁移）。
- 新建 `app/ui/styles_dark.qss`：以 `release/.../styles_dark.qss` 为蓝本落入源码目录。
- 删除 `app/ui/styles.qss`（其内容已迁移到 `styles_light.qss`，且无其他引用）。
- 理由：与历史 release 产物命名一致、语义清晰、便于将来扩展；非无关重构，直接服务主题功能。

### 4.3 `app/main.py` 按主题加载 QSS

替换 42-44 行：

```python
from app.utils.theme import get_theme
...
theme = get_theme()
qss_name = "styles_light.qss" if theme == "light" else "styles_dark.qss"
qss_path = get_resource_path("app", "ui", qss_name)
if qss_path.exists():
    app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
log_service.info(f"主题: {theme}")  # 复用已存在的 log_service
```

### 4.4 `app/ui/drop_zone.py` 内联 QSS 取色

- `__init__`、`dragEnterEvent`、`dragLeaveEvent`、`dropEvent` 中的 `setStyleSheet` 改为用 `palette()` 颜色填充（f-string / `.format`）。
- 两行标签颜色同样取 `palette()["dz_label"]` / `["dz_sublabel"]`。
- 逻辑/事件处理不变，仅替换颜色字面量。

### 4.5 `app/ui/main_window.py` 自绘与标签取色

- `PackTableDelegate.paint()`：每次绘制时调用 `palette()` 取色（字典查找，开销可忽略；且为将来运行时切换留出刷新点），替换 61-70 / 92 / 100 / 104 / 114 / 118 处 `QColor(...)` 字面量。
- `_create_folder_icon()` / `_create_trash_icon()`：取 `palette()["folder_icon"]` / `["trash_icon"]`。注意这两个图标在 `__init__` 创建一次；启动时主题已定，可接受。运行中切换主题需重建图标——属后续项。
- 状态标签 `setStyleSheet`（336 / 358 / 367 / 401 / 411 / 727 / 765 / 768 / 781 / 786 / 797 / 801）：颜色字面量替换为 `palette()` 对应键（成功/错误/提示/标题/文件色）。文案、字号、字重不变。

### 4.6 打包配置 `NeteaseResourcepackManager.spec`

datas 由 `styles.qss` 改为 `styles_light.qss` + `styles_dark.qss`：

```python
datas=[
    (str(project_root / 'app' / 'ui' / 'styles_light.qss'), 'app/ui'),
    (str(project_root / 'app' / 'ui' / 'styles_dark.qss'), 'app/ui'),
    (str(project_root / 'app' / 'ui' / 'icon.ico'), 'app/ui'),
],
```

### 4.7 新增 `tests/test_theme.py`

- `get_theme()`：mock `winreg` 读取 `AppsUseLightTheme=1`→`"light"`、`=0`→`"dark"`、键缺失/异常→`"light"`、非 Windows（`winreg` 不可导入）→`"light"`。
- `palette()`：light/dark 两个字典都含全部约定键，且对应主题返回正确字典。
- 不依赖真实注册表，全部用 `unittest.mock`（避免污染用户系统）。

## 5. 修改文件清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `app/utils/theme.py` | 新增 | 注册表读取 + 调色板 |
| `app/ui/styles_light.qss` | 新增 | 现有浅色 QSS 内容迁移 |
| `app/ui/styles_dark.qss` | 新增 | 参考 `release/.../styles_dark.qss` |
| `app/ui/styles.qss` | 删除 | 内容已迁入 `styles_light.qss` |
| `app/main.py` | 修改 | 按主题选 QSS（42-44 行） |
| `app/ui/drop_zone.py` | 修改 | 内联 QSS/标签颜色取 `palette()` |
| `app/ui/main_window.py` | 修改 | `PackTableDelegate` 自绘 + 状态标签取 `palette()` |
| `NeteaseResourcepackManager.spec` | 修改 | datas 替换为两个 QSS 文件 |
| `tests/test_theme.py` | 新增 | 主题判定与调色板单测 |

## 6. 不应修改

- `app/services/*`（扫描/导入/替换/备份/回滚/删除/日志）、`app/models/*`、`app/utils/manifest.py`、`app/utils/shell.py`、`app/utils/runtime_paths.py`、`app/config.py`——业务与路径逻辑保持不变。
- `README.md`、`AGENTS.md`、`.gitignore`、`LICENSE`——默认不动（README 是否需补充主题说明见第 9 节待确认）。
- `build/`、`dist/`、`release/`、`.pyi_build/`——构建/发布产物，不作为源码修改对象。
- `requirements.txt`——`winreg` 为标准库，不新增依赖。
- 不新增 UI 按钮、设置页、运行中切换逻辑。

## 7. 验证方案

1. 单元测试（必跑）：
   ```powershell
   python -m unittest discover -s tests -v
   ```
   期望 `test_theme.py` 全过，且原有 5 个测试不受影响。
2. 源码运行——浅色：注册表保持 `AppsUseLightTheme=1`（或删除键），`python -m app.main`，确认窗口/卡片/拖拽区/状态标签为浅色，与现状一致。
3. 源码运行——深色：将 `AppsUseLightTheme` 改为 `0`（regedit 或 PowerShell `Set-ItemProperty`），重启程序，确认：窗口背景深、列表卡片深底浅字、选中/hover 态深色协调、拖拽区深底浅边框、成功/错误标签颜色在深底上可读。验证后改回原值。
4. 打包验证：
   ```powershell
   python -m PyInstaller --noconfirm NeteaseResourcepackManager.spec
   ```
   确认 `dist/.../app/ui/` 下同时存在 `styles_light.qss` 与 `styles_dark.qss`；启动 exe，分别在两种系统主题下确认样式正确；AppData 下 `backups`/`logs`/`temp` 正常。
5. 回归：导入校验、替换/回滚、删除、刷新滚动等核心流程在深浅两色下各跑一次，确认行为不受样式改动影响。

## 8. 风险

- **winreg 仅 Windows 可用**：`try/except ImportError` 回退浅色，非 Windows 仍可启动与测试。
- **注册表键缺失/被策略禁用**：`get_theme()` 捕获 `FileNotFoundError`/`PermissionError`，回退浅色。
- **内联颜色替换遗漏**：深色下个别元素仍浅色。靠逐处比对（第 3 节列出的全部行号）+ 两种主题实机核对控制。
- **运行中切换系统主题不自动刷新**：本次仅启动判定；自绘 `paint()` 已取实时 `palette()`，但全局 QSS 与图标需重启生效。列为后续项，可在后续用 `QFileSystemWatcher` 监听注册表导出文件或定时轮询 + 重新 `setStyleSheet`/重建图标实现。
- **打包遗漏 QSS**：`.spec` datas 必须含两个 QSS，否则打包后深色回退浅色（`qss_path.exists()` 为假时静默跳过）。靠第 7 步打包验证控制。
- **图标颜色在运行中切换不刷新**：folder/trash 图标在 `__init__` 固化，属后续项范畴。

## 9. 待人工确认项

- 是否需要同步在 `README.md` 补充一句「软件跟随系统深/浅色模式」的用户可见说明？默认不改 README，按 AGENTS.md 规则保持不动，待确认。
- `app/utils/__pycache__/theme.cpython-313.pyc`、`tests/__pycache__/test_theme.cpython-313.pyc` 两个残留缓存是否清理？属构建缓存，不影响功能，建议本次顺手删除以避免误以为是有效产物；若不希望动 `__pycache__`，则保留。
- 深色 `success` 色用 `#34D399`（更亮、深底可读）还是沿用浅色的 `#059669`？当前方案选 `#34D399`（对齐 `styles_dark.qss` 的 `SuccessLabel` 思路），如希望两色完全一致可调整。
