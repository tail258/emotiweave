# EmotiWeave｜情绪织谱

EmotiWeave（情绪织谱）是一个本地运行的多模态情绪观察与对话工具。它融合摄像头、文本和语音韵律中的可观察线索，生成连续的效价—激活状态、置信度和冲突说明，并允许用户随时纠正判断。

系统不将线索估计解释为真实情绪，也不用于心理诊断或人员评估。

## 功能

- **连续状态跟踪**：对视觉线索进行时间平滑、迟滞处理和 1.5 秒过期控制。
- **三模态融合**：分别处理面部、文本和语音韵律证据，并按置信度融合。
- **冲突说明**：区分视觉—文本效价冲突、视觉—语音激活冲突和文本—语音激活冲突。
- **可解释语音特征**：提取能量、动态范围、音高中位数、音高变化、语速、停顿比和有声占比。
- **本地对话**：通过 Ollama 流式生成回复，启动时后台预热并保持模型驻留；不可用时保留确定性降级回复。
- **用户纠正**：支持积极、消极、准确和暂不判断四种校正操作。
- **数据最小化**：默认不保存原始音视频或对话文本，仅记录必要的派生状态与运行信息。

## 环境要求

- Windows
- Python 3.11 或 3.12
- 可选：Ollama

## 安装

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.11 -m pip install --upgrade pip
py -3.11 -m pip install -e .
py -3.11 scripts\download_models.py
py -3.11 main.py --check
```

启用本地对话：

```powershell
ollama serve
ollama pull qwen2.5:3b
```

模型名称、服务地址、超时时间、启动预热、流式输出和驻留时间可在
`config.yaml` 的 `brain` 节中调整。`warmup_on_start` 与 `stream` 默认开启，
`keep_alive` 默认设为 15 分钟。

## 启动

一键启动：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\start.ps1
```

或直接启动：

```powershell
py -3.11 main.py
```

默认地址为 `http://127.0.0.1:7860/`。

## 使用

1. 允许浏览器访问摄像头，系统开始生成连续视觉状态。
2. 输入文字或录制语音，系统融合当前会话中的多模态线索。
3. 查看效价—激活轨迹、置信度和冲突原因。
4. 使用校正按钮修正当前判断或暂时关闭判断。
5. 在“查看派生证据”中检查各模态的可解释输入。

## 验证

```powershell
py -3.11 -m pytest -q
py -3.11 main.py --check
```

核心领域测试不依赖摄像头、麦克风或 Ollama。

## 离线情绪识别评估

评估以连续效价—激活度为主输出，同时报告派生离散标签的准确率、宏平均 F1、Unknown 率、混淆矩阵和三类模态冲突的 precision/recall/F1。参与者数据与确定性脚本回归分开统计；脚本样本不能被当作真实人群准确率。

建立并校验标注数据集：

```powershell
py -3.11 scripts\collect_evaluation_sample.py --validate data\evaluation\manifest.jsonl
```

开发集回放和参数搜索：

```powershell
py -3.11 scripts\replay_scenarios.py `
  --dataset data\evaluation\manifest.jsonl `
  --config config.yaml `
  --split dev `
  --output reports\evaluation\runs\dev-default\predictions.jsonl

py -3.11 scripts\tune_fusion.py `
  --dataset data\evaluation\manifest.jsonl `
  --config config.yaml `
  --output reports\evaluation\tuning
```

冻结配置后，只对留出的测试集运行一次：

```powershell
py -3.11 scripts\replay_scenarios.py `
  --dataset data\evaluation\manifest.jsonl `
  --config config.yaml `
  --split test `
  --output reports\evaluation\runs\test-final\predictions.jsonl

py -3.11 scripts\evaluate_sessions.py `
  --predictions reports\evaluation\runs\test-final\predictions.jsonl `
  --output reports\evaluation\final
```

脚本冲突回归不需要摄像头、麦克风、Ollama 或 Whisper：

```powershell
py -3.11 scripts\replay_scenarios.py `
  --dataset evaluation\datasets\scripted_conflicts.jsonl `
  --config config.yaml `
  --split scripted `
  --output reports\evaluation\runs\scripted\predictions.jsonl
```

## 结构

```text
src/sentientbot/
├── affect/       # 校准、时序跟踪、三模态融合与响应策略
├── evaluation/   # 标注数据、离线回放、指标、参数搜索与报告
├── perception/   # 面部、文本、ASR 与语音韵律分析
├── dialogue/     # Ollama 与本机语音播报
├── storage/      # 隐私约束下的事件日志
├── ui/           # Gradio 工作界面
├── app.py        # 应用编排
├── config.py     # 配置模型
├── models.py     # 领域数据
└── session.py    # 会话状态
```

详细设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 使用边界

- 不用于心理诊断、医疗建议、招聘筛选、课堂监控或其他人员评估。
- 语音韵律只参与激活度估计，不直接推断积极或消极效价。
- 情绪状态始终是可纠正的观察结果，以用户自述为准。
- 默认配置只适合本机单用户运行；开放远程访问前需要补充身份验证、访问控制和数据保留策略。
