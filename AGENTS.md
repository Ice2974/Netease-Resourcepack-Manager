# AGENTS.md

本文件是给 Agent 使用的仓库工作规则，只记录协作方式、修改边界、项目不变量和验证要求，不维护版本流水账或发布历史。

## 信息来源

- 项目事实以当前源码、`README.md`、测试、打包配置为准，`AGENTS.md` 只提供工作规则。
- 修改前先阅读本次任务相关的源码、配置、测试和文档，不要只根据文件名猜测实现。
- 如果 `AGENTS.md` 与源码、测试、`README.md` 或 `docs/` 冲突，以源码、测试和文档为准，并在回复中说明冲突。
- 不要根据 `AGENTS.md` 推断当前版本号、已发布版本、历史变更或发布状态；版本与发布状态以源码、打包产物说明或用户给出的任务上下文为准。
- 不能验证的内容要明确说明，不能伪装为已测试或已确认。

## 基本原则

- 优先做最小必要修改，不做与任务无关的重构、格式化、依赖升级、UI 重做或发布配置调整。
- 默认保持 Windows 绿色版 / 目录版定位，不引入安装器、后台服务、联网服务或账号体系。
- 默认保持本地离线工具定位，不新增联网、云材质下载、启动器联动、自动进服 / 重进游戏、安卓适配、历史版本管理界面或多包批量替换功能，除非用户明确要求。
- 涉及资源包替换、备份、回滚、日志、路径处理时，优先保证数据安全和可回滚，不为了简化代码牺牲安全边界。
- 对实现范围、Windows 路径兼容性、PyInstaller 打包兼容性、网易资源包结构差异或验证结果不确定时，写入回复的“待人工确认项”。
- 单次任务提示词只补充本次任务特有要求；未重复说明的通用约束仍以本文件为准。

## 固定项目标识

以下为项目长期固定命名，除非任务明确要求重命名，否则不要修改：

| 标识类型 | 固定值 |
|---|---|
| 项目名称 / Display Name | `Netease Resourcepack Manager` |
| 窗口标题 | `Netease Resourcepack Manager` |
| 技术栈 | Python + PySide6 |
| 目标平台 | Windows |
| 分发形态 | PyInstaller `onedir` / 免安装目录版 |
| 用户数据目录 | `%AppData%\NeteaseResourcepackManager` |
| 网易资源包缓存目录 | `%AppData%\MinecraftPE_Netease\packcache` |
| 推荐发布目录 | `release\NeteaseResourcepackManager\` |
| 发布启动文件 | `release\NeteaseResourcepackManager\NeteaseResourcepackManager.exe` |

约束：

- 窗口标题默认不显示版本号；除非用户明确要求，不要把版本号加入窗口标题。
- 如果修改项目名称、exe 名称、发布目录或 AppData 目录，必须同步检查 `.spec`、构建脚本、运行时路径、UI 标题、README / docs 和相关测试。
- 如果修改版本号，必须全文搜索旧版本号残留，并同步所有实际承担版本来源的文件；历史记录、示例或 release notes 中的旧版本号不确定时不要擅自改写，写入“待人工确认项”。

## 目录边界

- `app/main.py`：程序入口、依赖组装、QSS 加载。
- `app/config.py`：AppData 路径与数据目录初始化。
- `app/models/`：资源包与操作结果等数据模型。
- `app/services/`：扫描、导入校验、替换、备份、日志等核心业务逻辑。
- `app/ui/main_window.py`：主界面与导入界面。
- `app/ui/drop_zone.py`：拖拽导入区域。
- `app/ui/styles.qss`：统一样式。
- `app/utils/manifest.py`：`manifest.json` 读取与资源包名称提取。
- `app/utils/shell.py`：打开目录 / 定位文件等 Windows Shell 辅助逻辑。
- `app/utils/runtime_paths.py`：源码运行与 PyInstaller 打包运行时的资源路径兼容。
- `tests/`：核心服务和回归测试。
- `scripts/build_release.ps1`：推荐发布构建脚本。
- `NeteaseResourcepackManager.spec`：PyInstaller 打包配置。
- `build/`、`dist/`、`release/`、`.pyi_build/`：构建或发布产物目录，默认不作为源码修改对象。

## 功能边界

当前默认支持的核心能力：

- 扫描 `%AppData%\MinecraftPE_Netease\packcache` 一级资源包目录。
- 导入并校验 `.zip` / `.mcpack`。
- 执行替换，并严格保留目标资源包原 `manifest.json`。
- 替换前自动备份，失败时自动回滚，支持手动回滚最近一次替换前状态。
- 记录操作日志，并提供日志目录查看入口。

默认不实现或不扩展的能力：

- 联网功能。
- 云材质下载。
- 启动器联动。
- 自动进服 / 重进游戏。
- 安卓 / MacOS 适配。
- 历史版本管理界面。
- 多包批量替换。

如果任务涉及上述默认不包含能力，需要先在计划或回复中明确它会扩大功能边界，并说明涉及的风险、验证成本和可能影响的目录。

## 数据目录与运行时文件

- 运行时数据统一写入 `%AppData%\NeteaseResourcepackManager`。
- 子目录固定为：`backups`、`logs`、`temp`。
- `temp` 应在启动时自动清理，不应依赖用户手动删除。
- 不要把运行时备份、日志、临时文件写入源码目录或发布目录。
- 修改路径逻辑时必须兼容 Windows 用户目录、空格、中文路径和 PyInstaller 打包运行场景。
- 涉及删除、覆盖、移动真实资源包文件时，必须优先使用安全的临时目录、备份和异常回滚流程。

## 扫描规则

- 默认只扫描 `packcache` 的一级子目录，不递归深扫多级目录。
- 子目录包含 `manifest.json` 即视为可管理资源包。
- 资源包名称优先读取 `manifest.json -> header.name`，读取失败或字段缺失时回退目录名。
- 图标优先使用资源包目录内 `pack_icon.png`，缺失时使用占位图标。
- 扫描失败、单个资源包 manifest 解析失败或图标缺失，不应导致整个程序崩溃；应降级显示并记录必要日志。

## 导入校验规则

- 默认只接受 `.zip` 和 `.mcpack`。
- 必须校验导入包内存在可解析的 `manifest.json`。
- 必须校验关键结构：`format_version`、`header`、`modules`。
- 需要支持外层包裹目录，例如 `MyPack/manifest.json`。
- 对无效压缩包、缺失 manifest、manifest JSON 解析失败或关键结构缺失，应返回明确错误，不进入替换流程。
- 不要因为导入包 manifest 合法就覆盖目标包原 `manifest.json`；目标 manifest 保留规则优先级更高。

## 替换与回滚规则

- 替换前必须创建目标资源包目录的完整备份。
- 替换时目标目录中仅保留原 `manifest.json`，其余内容按既有替换逻辑清理。
- 复制导入包内容时，必须跳过导入包根 `manifest.json`，确保目标包原 `manifest.json` 不被替换。
- 任一步失败必须自动回滚，避免半替换状态。
- 手动回滚默认只回滚最近一次替换前状态。
- 回滚过程、失败原因和关键异常必须写入日志。
- 不要把“替换成功”写入日志或 UI，除非复制、清理和必要校验都已完成。

## UI 与交互边界

- 主界面资源包列表默认保持单列卡片化展示。
- 行右侧黑白文件夹图标用于打开对应资源包目录。
- 操作按钮不应出现焦点虚线框回退；修改 QSS 或按钮 focus 策略时必须检查该问题。
- 窗口标题固定为 `Netease Resourcepack Manager`，默认不显示版本号。
- UI 文案应面向普通 Windows 用户，避免把内部异常、Python 栈信息或实现细节直接暴露为主要提示。
- 修改 UI 时不要顺手重做整体视觉风格、布局体系或交互流程；除非任务明确要求。

## 打包与发布规则

- 默认使用 PyInstaller `onedir` 方案。
- 发布目录必须包含 Python 运行时与依赖，用户不需要安装 Python / pip。
- `app/ui/styles.qss` 必须作为 data 资源加入 `.spec`。
- `app/main.py` 应通过 `get_resource_path("app", "ui", "styles.qss")` 加载样式，兼容源码运行与 PyInstaller 打包运行。
- 推荐发布目录为 `release\NeteaseResourcepackManager\`，分发时应分发整个目录。
- `build\...` 下 exe 是中间产物，不应作为正式发布程序给用户运行。
- 修改 `.spec`、资源路径、QSS 加载、发布脚本或依赖时，必须验证源码运行与打包运行两个场景。

## 依赖与兼容性

- 不要无任务需求升级 PySide6、PyInstaller 或其他依赖。
- 新增依赖前先判断能否用标准库或现有依赖解决；如必须新增，说明原因、影响和打包验证要求。
- 路径处理优先使用 `pathlib` / 标准库跨路径写法，不硬编码开发者本机绝对路径。
- Windows Shell 行为、AppData 路径、中文路径、空格路径和无 Python 环境的发布目录运行都属于关键兼容点。

## 文档与 README

- `README.md` 面向普通用户，默认不要改成开发流水账或 Agent 指令。
- `AGENTS.md` 面向 Agent，默认不要写成用户教程、版本发布说明或当前状态清单。
- 若存在 `docs/`，开发说明、设计记录、发布说明等项目资料优先放入 `docs/`，不要塞进 `AGENTS.md`。
- 文档只维护当前有效状态，不追加无关历史流水账。
- 修改用户可见行为、运行命令、发布方式或功能边界时，需要同步检查 README / docs 是否需要更新；如果任务不允许修改，写入“待人工确认项”。

## 构建与验证

常用命令：

```powershell
pip install -r requirements.txt
python -m app.main
python -m unittest discover -s tests -v
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
python -m PyInstaller --noconfirm NeteaseResourcepackManager.spec
```

验证要求：

- 只修改 Markdown 文档时，至少运行 `git diff --check`。
- 修改 Python 源码、核心服务、UI、QSS、路径工具或测试时，至少运行 `python -m unittest discover -s tests -v`。
- 修改打包配置、资源加载、依赖或发布脚本时，运行发布构建脚本或等价 PyInstaller 命令。
- 打包相关修改需要确认发布 exe 可启动，`styles.qss` 在打包产物中存在，AppData 下 `backups`、`logs`、`temp` 能正常创建与写入。
- 如果因环境限制无法运行验证命令，需要在回复中明确说明未验证内容、原因和风险。
- 不要把未运行的源码启动、打包启动、真实网易 Minecraft 环境测试写成已通过。

## 日志与测试边界

- 日志应覆盖导入失败、替换失败、回滚失败、路径异常、压缩包异常和关键文件操作异常。
- 不要在正常操作路径中输出过量日志。
- 不要把用户隐私、无关环境信息或完整敏感路径作为不必要日志内容；必要路径信息应服务于排障。
- 单元测试优先覆盖扫描、导入校验、替换、备份、回滚、manifest 解析和路径兼容。
- Agent 可以运行自动化测试、补充测试清单、生成手工验收步骤，但不负责最终真实游戏环境验收。

## 默认不要修改

除非任务明确要求，默认不要修改：

- `README.md`
- `.gitignore`
- `LICENSE`
- `AGENTS.md`
- `build/`
- `dist/`
- `release/`
- `.pyi_build/`
- 用户本机 AppData 数据目录
- 与当前任务无关的构建脚本、发布配置和依赖文件

涉及上述文件或目录但任务没有明确要求时，先在计划或回复中说明是否需要修改；不确定时写入“待人工确认项”。

## 回复要求

完成任务后，回复中说明：

- 修改了哪些文件。
- 为什么这样改。
- 运行了哪些验证命令。
- 哪些内容未验证，以及原因。
- 待人工确认项；如果没有，就写“无”。
- 是否发现与 README、docs 或现有源码不一致的地方。
