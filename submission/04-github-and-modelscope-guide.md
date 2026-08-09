# GitHub 与 ModelScope 人工发布指南

本指南只提供操作步骤。GitHub 建库、公开推送、ModelScope 发布和赛方提交均由参赛者本人
完成。

## 0. 重要前置状态

当前工作区的 `.git` 目录不是有效 Git 仓库，且公网托管适配尚未实施。现有本地应用仍是
单用户架构，会共享会话状态，并依赖本机配置。因此：

- 可以先整理并发布当前源码仓库；
- 不能把当前本地程序直接当成已经可用的 ModelScope 公网 Demo；
- 必须先完成公网启动入口、配置降级、会话隔离和托管验证；
- 正式作品链接只能使用通过无痕窗口验收后的公开 App URL。

公网适配设计位于：

`D:\工作区\SentientBot_V2\docs\superpowers\specs\2026-08-09-public-submission-link-design.md`

## 1. 发布前本地验证

打开 PowerShell：

```powershell
Set-Location 'D:\工作区\SentientBot_V2'
py -3.11 -m pytest -q
py -3.11 -m ruff check src scripts tests
py -3.11 main.py --check
```

只有测试和代码检查通过后再发布。

## 2. 初始化本地 Git 仓库

先确认当前目录：

```powershell
Get-Location
Get-ChildItem -Force .git
```

然后在项目根目录初始化：

```powershell
git init -b main
git config user.name
git config user.email
```

如果后两条没有输出，设置你希望显示在提交记录中的身份：

```powershell
git config user.name '你的公开显示名称'
git config user.email '你的 GitHub 提交邮箱'
```

这些设置只写入当前仓库，不使用 `--global`。

## 3. 只暂存允许公开的文件

不要使用整体暂存命令。按清单执行：

```powershell
git add -- .gitignore README.md main.py start.ps1 config.yaml pyproject.toml requirements.txt
git add -- src scripts tests evaluation submission
git add -- assets/models/.gitkeep docs/ARCHITECTURE.md
git add -- reports/evaluation/scripted-final/metrics.md
git add -- reports/evaluation/scripted-final/summary.json
git add -- reports/evaluation/scripted-final/confusion_matrix.csv
git add -- reports/evaluation/scripted-final/per_sample.csv
```

检查暂存内容：

```powershell
git status --short
git diff --cached --stat
git diff --cached --name-only
```

如果发现隐私数据、缓存、日志、HTML 大文件或凭据，使用以下非破坏性命令将单个路径移出
暂存区，然后再次检查：

```powershell
git restore --staged -- '不应公开的相对路径'
```

该命令不会删除本机文件。

## 4. 创建首次提交

确认暂存清单无误后：

```powershell
git commit -m 'feat: release EmotiWeave emotion recognition project'
git status --short
```

首次提交后 `git status --short` 可以显示未跟踪的本机材料，但不能显示意外修改或已经暂存的
敏感文件。

## 5. 在 GitHub 创建空仓库

1. 登录 GitHub。
2. 点击右上角“+”并选择“New repository”。
3. Repository name 使用 `emotiweave`。
4. Description 建议填写：
   `Correctable multimodal emotion recognition with valence-arousal tracking and conflict detection.`
5. 选择 Public。
6. 不勾选自动创建 README、`.gitignore` 或 License，保持远程仓库为空。
7. 点击“Create repository”。
8. 复制页面显示的 HTTPS 仓库地址。

## 6. 连接远程仓库并推送

在 PowerShell 中设置变量并推送：

```powershell
$GitHubRepoUrl = Read-Host '粘贴 GitHub HTTPS 仓库地址'
git remote add origin $GitHubRepoUrl
git remote -v
git push -u origin main
```

如果提示浏览器认证，使用你自己的 GitHub 账号完成。不要把访问令牌写入项目文件、命令历史
示例或提交材料。

推送完成后，在未登录 GitHub 的无痕窗口打开仓库主页，确认：

- README 能正常显示；
- 源码、测试和运行说明可见；
- 没有会话日志、参与者数据、个人路径文件或凭据；
- `reports/evaluation/scripted-final/metrics.md` 明确说明是脚本工程回归；
- 安装和测试命令可复制。

## 7. 完成公网托管适配

创建 ModelScope 创空间之前，按照公网部署设计实施并验证：

- 独立公网配置和托管启动入口；
- 禁用 Ollama、TTS、Whisper 和持久日志；
- 保留面部、文本和语音韵律识别；
- 按浏览器隔离校准、轨迹、历史和纠正；
- Face Landmarker 自动准备与失败降级；
- 最大会话数、空闲回收、录音和队列限制；
- 首屏体验步骤和隐私提示；
- 两个无痕窗口不会共享状态。

这些功能尚未实施时，不要声称 ModelScope 版本已经可用，也不要把本地临时链接填入赛方
表单。

## 8. 创建 ModelScope 创空间

公网适配代码合并并重新推送 GitHub 后：

1. 登录 ModelScope。
2. 进入“创空间”并选择创建新空间。
3. 空间名称建议使用 `EmotiWeave｜情绪织谱`，英文标识建议使用 `emotiweave`。
4. 可见性选择公开。
5. SDK 选择 Gradio。
6. 填写中文简介，内容可从 `submission/01-form-content.md` 精简复制。
7. 按平台支持方式从 GitHub 导入，或上传 `submission/03-source-manifest.md` 允许的文件。
8. 配置公网启动入口和 Python 依赖；不要上传 `.env`、令牌或本机模型缓存。
9. 启动构建并查看构建日志。
10. App 状态变为 Running 后复制公开 App URL。

如果平台不支持直接导入完整仓库，只上传公网运行所必需的入口、配置、`src/`、依赖文件、
模型下载脚本和 README；测试和离线报告仍保留在 GitHub。

## 9. 公网验收

用未登录 ModelScope 的无痕窗口打开 App URL，逐项验证：

1. 无需登录即可进入页面。
2. 页面通过 HTTPS 加载。
3. 摄像头权限允许后可以完成约 4 秒基线。
4. 表情变化会更新效价—激活状态和轨迹。
5. 文字输入会产生文本证据并参与融合。
6. 同时提交文字和录音会产生韵律证据。
7. 冲突场景会降低置信度并给出原因。
8. 清空会话能恢复初始状态。
9. 第二个无痕窗口看不到第一个窗口的轨迹或纠正。
10. 页面没有暴露服务器路径、堆栈、令牌或其他用户内容。

建议再使用手机流量打开一次，确认中国大陆网络访问和移动布局可用。

## 10. 最终链接使用

- 赛方“作品访问链接”：填写验收通过的 ModelScope App URL。
- ModelScope 说明页：加入 GitHub 仓库 URL。
- GitHub README：加入 ModelScope App URL。
- 不使用本机地址。
- 不使用依赖电脑持续在线且会过期的 Gradio 临时分享链接。
