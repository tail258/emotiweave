# EmotiWeave｜情绪织谱项目运行说明

## 1. 项目简介

EmotiWeave 是一个本地优先的多模态情绪观察与识别工具。系统融合摄像头面部线索、文字
线索和语音韵律，输出连续效价—激活状态、置信度、变化轨迹及模态冲突说明，并允许用户
纠正当前判断。

系统估计的是当前可观察线索，而非用户真实内心状态，不用于心理诊断、医疗建议、招聘
筛选、课堂监控或其他人员评估。

## 2. 在线体验

公开版本部署完成后，使用方式如下：

1. 用 Chrome 或 Edge 打开公开 ModelScope 创空间 App。
2. 允许网页访问摄像头，并保持自然表情约 4 秒完成个人基线。
3. 改变表情，观察效价、激活度、置信度和轨迹变化。
4. 输入文字，观察视觉与文本线索融合后的状态。
5. 如需体验语音韵律，同时录音并输入刚才说出的文字。
6. 展开“查看派生证据”，检查各模态实际参与融合的线索。
7. 使用校正按钮修正当前判断，或点击“清空会话”重新开始。

公网版本不保存原始音视频或对话文本，并关闭本地 Ollama、语音播报和 Whisper 转写；
本地完整版仍可选择启用这些能力。

## 3. 本地环境要求

- Windows 10 或 Windows 11；
- Python 3.11 或 3.12，推荐 Python 3.11；
- 摄像头；
- 可选麦克风；
- 可选 Ollama，用于本地流式对话。

## 4. 安装

在 PowerShell 中进入项目目录：

```powershell
Set-Location 'D:\工作区\SentientBot_V2'
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -e .
py -3.11 scripts\download_models.py
py -3.11 main.py --check
```

如果 PowerShell 不允许执行激活脚本，可仅对当前窗口临时放行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## 5. 启动

一键启动：

```powershell
.\start.ps1
```

或直接运行：

```powershell
py -3.11 main.py
```

默认本地地址为 `http://127.0.0.1:7860/`。

## 6. 可选的本地 Ollama 对话

Ollama 不影响情绪识别核心。若要启用本地模型回复：

```powershell
ollama serve
ollama pull qwen2.5:3b
py -3.11 main.py
```

Ollama 不可达时，系统使用确定性降级回复，面部、文本、语音韵律和融合状态仍然可用。

## 7. 技术架构

```text
摄像头 → MediaPipe Face Landmarker → 个人基线与时序跟踪 ┐
文字   → 可解释中文文本线索                             ├→ 置信度加权融合
录音   → 能量、音高、语速、停顿等韵律特征               ┘       ↓
                                                        连续效价—激活状态
                                                               ↓
                                                轨迹、冲突说明、用户纠正
```

主要模块：

- `src/sentientbot/perception/`：面部、文本、ASR 与语音韵律分析；
- `src/sentientbot/affect/`：校准、时序跟踪、融合和交互策略；
- `src/sentientbot/evaluation/`：数据校验、回放、指标、搜索和报告；
- `src/sentientbot/ui/`：Gradio 用户界面；
- `src/sentientbot/session.py`：会话状态、历史与纠正；
- `src/sentientbot/app.py`：应用编排和降级处理。

## 8. 情绪识别与融合原则

- 视觉使用个人基线、连续时间平滑和 1.5 秒线索过期控制。
- 文本同时估计效价和激活度。
- 语音韵律只估计激活度，不直接推断积极或消极效价。
- 各模态按置信度和配置权重融合。
- 可靠模态明显相反时记录冲突并降低总体置信度。
- 证据不足时输出 Unknown 或保持正常对话，不强行判断。
- 用户纠正优先，并只影响当前会话。

## 9. 验证

运行单元测试和代码检查：

```powershell
py -3.11 -m pytest -q
py -3.11 -m ruff check src scripts tests
py -3.11 main.py --check
```

运行不依赖摄像头、麦克风、Ollama 或 Whisper 的脚本冲突回归：

```powershell
py -3.11 scripts\replay_scenarios.py `
  --dataset evaluation\datasets\scripted_conflicts.jsonl `
  --config config.yaml `
  --split scripted `
  --output reports\evaluation\runs\scripted\predictions.jsonl

py -3.11 scripts\evaluate_sessions.py `
  --predictions reports\evaluation\runs\scripted\predictions.jsonl `
  --output reports\evaluation\scripted
```

脚本样本只验证融合、报告和冲突检测的工程行为，不代表真实参与者准确率。真实人群性能
必须使用经过同意、按参与者隔离的开发集和测试集另行报告。

## 10. 隐私与数据边界

默认配置：

- 不保存摄像头帧；
- 不保存原始录音；
- 不记录对话文本；
- 仅在启用事件日志时记录必要派生状态和耗时；
- 用户可以清空当前会话；
- 项目不采集身份信息。

在公网部署前必须关闭事件日志、隔离不同浏览器会话、限制并发和录音时长，并使用 HTTPS。

## 11. 已知限制

- 表情和韵律会受到个体、文化、光照、镜头角度、麦克风和环境噪声影响。
- 文本线索分析是可解释规则，不等同于大型语言模型的完整语义理解。
- 当前公开指标主要来自确定性脚本回归，不能替代真实参与者评估。
- 本地应用原始实现是单用户架构，必须完成会话隔离后才能稳定公开给多名评委访问。
- 情绪识别只能作为可纠正的交互线索，不能作为高风险决策依据。

## 12. 常见问题

### 摄像头没有画面

确认浏览器已允许摄像头权限，并检查摄像头是否被其他软件占用。公网访问必须使用 HTTPS。

### 视觉模型不可用

运行 `py -3.11 scripts\download_models.py`，然后执行 `py -3.11 main.py --check` 查看状态。

### Ollama 不可用

这不会影响情绪识别。系统会使用确定性回复；也可以按照第 6 节启动 Ollama。

### 录音提交后没有结果

本地版可检查 faster-whisper 是否安装。公网版关闭 Whisper，必须同时输入文字才能进行
文本与韵律融合。
