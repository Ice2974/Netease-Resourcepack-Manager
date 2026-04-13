# Netease Resourcepack Manager

一个给网易版 Minecraft 基岩玩家使用的资源包替换工具（Windows 桌面版）。

> 目标：把“替换云材质内容”的繁琐手动流程，变成可视化、可回滚、可追踪日志的简单操作。

## 这是什么

在 EC 等服务器场景中，玩家通常需要先有一个已下载到本地的云材质，然后手动替换其中内容，才能加载自己的资源包。  
本工具就是把这套流程做成图形界面：

- 扫描本地 `packcache` 资源包
- 选择目标包
- 导入你的 `.zip` / `.mcpack`
- 自动校验、备份、替换
- 失败自动回滚
- 支持一键回滚到最近一次替换前状态

## 适用范围

- 系统：Windows
- 仅本地文件操作
- 不联网、不下载资源、不联动启动器

## 功能一览

- 自动扫描：`%AppData%\MinecraftPE_Netease\packcache`
- 显示资源包名称与图标
- 拖拽或选择 `.zip` / `.mcpack` 导入
- Bedrock 资源包基础合法性校验（含外层目录结构）
- 替换时保留目标资源包原 `manifest.json`
- 替换前自动备份
- 替换失败自动回滚
- 成功后支持“打开目标目录”“回滚到替换前”
- 日志记录与日志目录查看

## 给普通用户的使用方法（推荐）

如果你下载的是发布版压缩包：

1. 解压整个发布包到任意目录
2. 双击 `NeteaseResourcepackManager.exe`
3. 在主界面双击一个资源包进入导入界面
4. 拖入或选择你的 `.zip/.mcpack`
5. 校验通过后点击“执行替换”
6. 成功后按提示重进服务器生效

## 操作流程（详细）

1. 先在游戏/服务器里确保目标云材质已经下载到本地
2. 打开本工具，确认列表里能看到目标资源包
3. 双击目标资源包
4. 导入你的资源包文件（`.zip` 或 `.mcpack`）
5. 看到“校验通过”后执行替换
6. 若替换失败，工具会自动回滚；可点击“查看日志”排查

## 数据与文件位置

程序运行数据会写到：

- `%AppData%\NeteaseResourcepackManager\backups`
- `%AppData%\NeteaseResourcepackManager\logs`
- `%AppData%\NeteaseResourcepackManager\temp`

资源包扫描目录：

- `%AppData%\MinecraftPE_Netease\packcache`

## 常见问题

### 1）提示文件无法删除/覆盖
通常是游戏或启动器仍在占用文件。  
请先关闭 Minecraft / 启动器后重试。

### 2）导入文件被判定不合法
仅支持 `.zip` / `.mcpack`，并且压缩包内应包含可解析的 `manifest.json`。  
外层多一层文件夹是支持的。

### 3）替换后没有生效
请按提示重新进入服务器；必要时确认目标是否是你当前使用的云材质位。

### 4）如何恢复到替换前
替换成功后，在结果区域点击“回滚到替换前”。

## 安全说明

- 工具不会联网上传你的文件
- 工具不会修改目标资源包原 `manifest.json`
- 所有关键步骤都有日志，便于排查

## 免责声明

本工具为玩家自用辅助工具，仅处理本地文件。  
请自行承担使用风险，并遵守相关游戏与平台规则。

## 开发者运行（可选）

仅当你要从源码运行时需要：

```powershell
pip install -r requirements.txt
python -m app.main
```

## 打包说明（可选）

项目已提供单目录绿色版构建脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_release.ps1
```

发布目录：`release\NeteaseResourcepackManager\`  
请不要运行 `build\...` 下的中间产物 exe。
