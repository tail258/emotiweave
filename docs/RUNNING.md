# 本地运行说明

EmotiWeave 目前按 Windows 本机单用户环境设计。核心情绪识别可以在没有 Ollama 的情况下
运行；摄像头用于视觉线索，麦克风和本地语言模型都是可选项。

## 1. 环境要求

- Windows 10 或 Windows 11
- Python 3.11 或 3.12，推荐 Python 3.11
- Chrome 或 Edge
- 摄像头；麦克风可选
- Ollama 可选

先确认 Python Launcher 能找到合适的解释器：

```powershell
py -0p
py -3.11 --version
```

## 2. 安装

在 PowerShell 中进入克隆后的仓库目录：

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python scripts\download_models.py
python main.py --check
```

`download_models.py` 会把 MediaPipe Face Landmarker 下载到 `assets/models/`。模型文件不
提交到 Git，因此首次安装必须执行这一步。

## 3. 启动

激活虚拟环境后运行：

```powershell
.\start.ps1
```

脚本会先执行预检，然后启动 `http://127.0.0.1:7860/`。也可以直接运行：

```powershell
python main.py
```

常用参数：

```powershell
python main.py --check
python main.py --no-browser
python main.py --host 127.0.0.1 --port 7861
```

`--share` 会请求 Gradio 创建临时外网链接。该链接并不提供访问控制，不适合处理私人内容
或作为长期部署方式。

## 4. 使用流程

1. 浏览器询问权限时允许访问摄像头。
2. 保持自然表情片刻，等待会话内视觉基线建立。
3. 改变表情、输入文字或录制语音，观察效价、激活度和置信度变化。
4. 展开派生证据，检查各模态实际提供了什么线索。
5. 使用纠正按钮标记结果，或让系统暂时停止判断。
6. 点击清空会话可以重置历史和当前状态。

## 5. 可选的 Ollama 对话

Ollama 只影响回复生成，不影响情绪识别核心。

```powershell
ollama serve
ollama pull qwen2.5:3b
python main.py
```

默认模型是 `qwen2.5:3b`。如果服务不可用，应用会使用确定性降级回复。相关设置位于
`config.yaml` 的 `brain` 节。

## 6. 验证与开发

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src scripts tests main.py
python main.py --check
```

测试与脚本回归不需要摄像头、麦克风、Ollama 或 Whisper 模型。`main.py --check` 会报告
当前机器上的可用组件，因此某个可选服务不可用不等于测试失败。

## 7. 常见问题

### PowerShell 不允许执行脚本

只对当前 PowerShell 窗口临时放行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

### 找不到 `py -3.11`

安装 64 位 Python 3.11，安装时勾选 Python Launcher。已有 Python 3.12 时，也可以把上述
命令中的 `py -3.11` 改成 `py -3.12`。

### 视觉模型不可用

```powershell
python scripts\download_models.py
python main.py --check
```

同时确认 `assets/models/face_landmarker.task` 已生成。

### 摄像头没有画面

检查浏览器站点权限，并确认摄像头没有被会议软件或其他程序占用。关闭旧页面后重新启动
应用通常也能释放残留会话。

### 录音提交后没有转写

确认 `faster-whisper` 已安装。首次加载 Whisper 模型需要下载模型文件并可能耗时较长；即使
转写不可用，手动文字输入和语音韵律分析仍可独立工作。

### Ollama 无法连接

执行 `ollama serve`，然后检查 `config.yaml` 中的 `brain.host`。不需要本地对话时可以把
`brain.enabled` 设为 `false`。

## 8. 数据与部署边界

默认配置不保存摄像头帧或原始录音，`store_transcripts: false` 时也不记录对话原文。
派生事件日志默认写入 `data/sessions/`，可以通过 `privacy.log_events: false` 关闭。

当前应用没有身份认证、多用户会话隔离或 TLS。不要把监听地址改成公网地址后直接当作正式
服务使用；长期公网部署需要单独设计认证、会话、并发和数据删除策略。
