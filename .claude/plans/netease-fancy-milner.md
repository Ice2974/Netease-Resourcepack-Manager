# 为 Netease Resourcepack Manager 适配 Windows 默认应用模式（深/浅色）

## Context

当前软件只有一套浅色 QSS（`app/ui/styles.qss`），启动时在 [main.py:42-44](app/main.py) 一次性加载，无主题概念。需求是：读取 Windows「选择默认应用模式」注册表项，亮色时用浅色 QSS、暗色时用深色 QSS，不新增 UI 设置项、不新增依赖、不触碰业务逻辑。

探索发现：`release/` 构建产物里已存在 `styles_dark.qss`/`styles_light.qss`，但源码目录没有、spec 未打包、代码未引用，`__pycache__` 还有孤立 `theme.cpython-313.pyc`——说明该功能曾尝试过未落地。本次以最小方式正式实现。同时 [main_window.py](app/ui/main_window.py)（14 处）与 [drop_zone.py](app/ui/drop_zone.py)（6 处）的内联 `setStyleSheet` 硬编码浅色值，深色 QSS 覆盖不到，需最小统一为 QSS 接管。

已确认决策：
- 内联色值：最小统一，用 QSS 对象名/属性接管，不碰业务逻辑。
- 实时切换：不支持，仅启动时判定一次（实时监听列为后续项）。
- 文件命名：保留 `styles.qss`（浅色，不变）+ 新增 `styles_dark.qss`。

## 推荐方案

### 1. 新增 `app/utils/theme.py`（核心，纯标准库）

- `get_system_app_mode() -> str`：用 `winreg` 读取
  `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize`
  下的 `AppsUseLightTheme`（REG_DWORD）。`1`→`"light"`，`0`→`"dark"`。
  任何异常（键缺失、权限、非 Windows 平台无 `winreg`）一律降级返回 `"light"`，保证不崩溃。
- `get_qss_text() -> str`：根据 `get_system_app_mode()` 选择
  `get_resource_path("app", "ui", "styles.qss")`（浅色）或
  `get_resource_path("app", "ui", "styles_dark.qss")`（深色），
  读取返回文本；文件缺失时返回空串（与现状 `main.py` 的容错一致）。
- 复用 [runtime_paths.py](app/utils/runtime_paths.py) 的 `get_resource_path`，不新增路径逻辑。

### 2. 新增 `app/ui/styles_dark.qss`

以现有 `styles.qss` 结构为蓝本，替换色值为深色版（参考 `release/` 内已有 `styles_dark.qss` 的配色：页面背景 `#1F1F1F`、卡片 `#2B2B2B`、卡片边 `#3A3A3A`、正文 `#E5E7EB`、muted `#9CA3AF`、主色 `#3B82F6`、错误 `#F87171`、成功 `#34D399`），并补齐本次新增的对象名/属性选择器（见下）。

### 3. 修改 `app/main.py`

将 [main.py:42-44](app/main.py) 的 QSS 加载块改为：
```python
from app.utils.theme import get_qss_text
app.setStyleSheet(get_qss_text())
```
其余启动流程不变。

### 4. 内联色值统一为 QSS 接管（`main_window.py` / `drop_zone.py`）

原则：只改颜色来源，不改变量名、不碰业务分支、不调交互流程。

- **静态色**（`target_label` 近黑、`file_label`/`desc_label`/`mode_hint` muted 等）：
  给控件 `setObjectName(...)`，移除内联 `setStyleSheet` 中的颜色，改由
  `styles.qss` / `styles_dark.qss` 中 `#objectName { color: ... }` 定义。
- **状态色**（`validate_label`、`result_label` 的 成功/失败）：
  用动态属性 `setProperty("state", "success"|"error"|"hint")`，QSS 用
  `QLabel[state="success"] { color: ... }` 选择器；改属性后调用
  `widget.style().unpolish(widget); widget.style().polish(widget)` 触发刷新
  （PySide6 标准做法）。深浅 QSS 各定义一套状态色（浅色 `#059669/#DC2626`，深色 `#34D399/#F87171`）。
- **`drop_zone.py`**：虚线边框等结构性样式保留，仅把颜色值改为由 QSS 对象名接管（边框/文字/拖拽态色）。

### 5. 修改 `NeteaseResourcepackManager.spec`

在 `datas` 追加一行，使深色 QSS 进入打包产物：
```python
(str(project_root / 'app' / 'ui' / 'styles_dark.qss'), 'app/ui'),
```
打包方法（onedir）不变，仅多一个 data 资源。

### 6. 新增 `tests/test_theme.py`

- 读取逻辑：mock `winreg` 返回 `AppsUseLightTheme=0/1`，断言 `get_system_app_mode()` 返回 `"dark"`/`"light"`。
- 降级：模拟 `winreg.OpenKey` 抛 `FileNotFoundError`、模拟非 Windows 无 `winreg` 模块，断言返回 `"light"`。
- QSS 选择：mock 系统模式为 dark 时 `get_qss_text()` 返回的内容应来自 `styles_dark.qss`（可用唯一标记字符串验证）。
- 复用现有 `unittest` 风格（参考 [tests/test_services.py](tests/test_services.py)），不引入 pytest。

## 修改文件

| 文件 | 操作 |
|---|---|
| `app/utils/theme.py` | 新增 |
| `app/ui/styles_dark.qss` | 新增 |
| `app/main.py` | 改 QSS 加载块（约 2 行） |
| `app/ui/styles.qss` | 补本次新增的对象名/属性浅色定义 |
| `app/ui/main_window.py` | 内联色值 → objectName/property（仅颜色行，14 处） |
| `app/ui/drop_zone.py` | 内联色值 → objectName（仅颜色行，6 处） |
| `NeteaseResourcepackManager.spec` | `datas` 追加 `styles_dark.qss` |
| `tests/test_theme.py` | 新增 |

## 不应修改

- `app/services/*`（扫描/导入/替换/备份/回滚/删除/日志）
- `app/models/*`、`app/utils/manifest.py`、`app/utils/shell.py`
- `app/config.py` 路径与初始化逻辑
- `app/utils/runtime_paths.py`（仅复用）
- `README.md`、`AGENTS.md`、`.gitignore`、`LICENSE`
- `build/`、`dist/`、`release/`、`.pyi_build/`（构建产物）
- 打包方法（仍 onedir，不切 one-file）
- 不新增任何 UI 按钮/菜单/设置页
- 不新增依赖（`winreg` 为 Python 标准库，Windows 自带）

## 验证方案

1. 单元测试：`python -m unittest discover -s tests -v`（含新增 `test_theme.py`）。
2. 源码运行浅色：临时设注册表 `AppsUseLightTheme=1`，`python -m app.main`，确认浅色。
3. 源码运行深色：设 `AppsUseLightTheme=0`，`python -m app.main`，确认深色且内联标签（target/file/validate/result、drop_zone）可读、状态色正确。
4. 降级验证：临时让 `winreg.OpenKey` 失败（或非 Windows），确认默认浅色不崩溃。
5. 打包验证：`python -m PyInstaller --noconfirm NeteaseResourcepackManager.spec`，确认产物 `_internal/app/ui/` 下同时存在 `styles.qss` 与 `styles_dark.qss`；启动打包 exe 在深/浅两种系统模式下外观正确。
6. 回归：导入校验、替换、回滚、删除、刷新滚动等既有功能不受影响（跑相关测试）。

## 风险

- `styles_dark.qss` 配色与内联状态色迁移需目测，深色下对比度可能需微调。
- `setProperty` + `polish` 刷新在个别控件上若未触发需手动 `unpolish`/`polish`，需测试。
- 注册表项在极旧 Windows 版本可能不存在，已用降级兜底。
- 仅启动时判定：运行中切换系统主题不会刷新（已确认为本次可接受，实时监听 `WM_SETTINGCHANGE`/`ImmersiveColorSet` 列为后续项）。
- spec 追加 data 文件属于「打包资源」改动，非「打包方法」改动；按要求需同步验证打包产物。

## 待确认项

- 真实深色模式下各内联标签的实际可读性需人工目测验收（Agent 不负责真实游戏环境验收）。
- 是否需要后续补「运行中系统主题切换实时刷新」——本次不做，待用户后续提需求。
- `release/` 内既有 `styles_dark.qss`/`styles_light.qss` 为历史构建残留，本次不清理；如需统一清理可另行确认。
