# EmotiWeave｜情绪织谱

EmotiWeave 是我用来探索多模态情绪识别的一套本地应用。它不会把某个表情或某句话直接
等同于人的真实情绪，而是把摄像头、文字和语音韵律中能够观察到的线索放在一起，给出
连续的效价—激活度、置信度和模态冲突说明。判断不准确时，使用者可以立即纠正它。

这个项目最早来自一个桌面虚拟助手原型。后来我逐渐把重点收拢到情绪线索本身：不同模态
是否一致、证据何时过期、置信度从哪里来，以及系统不确定时应该怎样表达。现在仓库保留的
就是这部分能够在本地运行、测试和继续改进的实现。

> 这里的输出是对可观察线索的估计，不是心理诊断，也不应被用于招聘、教育监控、医疗或
> 其他针对个人的高风险判断。

## 现在能做什么

- 用 MediaPipe Face Landmarker 提取面部线索，并经过个人基线、时间平滑和过期控制生成
  连续视觉状态。
- 从中文文本中提取可解释的效价与激活线索。
- 从 WAV 录音中计算能量、音高变化、语速、停顿比和有声占比；语音韵律只参与激活度
  判断，不直接猜测积极或消极。
- 按置信度融合视觉、文本和语音证据，并指出模态之间的明显冲突。
- 在 Gradio 界面中查看状态轨迹、派生证据和冲突原因，并对当前结果进行纠正。
- 可选连接本机 Ollama 生成回复；Ollama 不可用时仍可使用情绪识别和确定性降级回复。
- 默认不保存摄像头帧和录音，也不记录对话原文。

## 环境

- Windows 10 或 Windows 11
- Python 3.11 或 3.12
- 摄像头；麦克风可选
- Ollama 可选，仅用于本地对话回复

## 安装与启动

在 PowerShell 中进入仓库目录后执行：

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python scripts\download_models.py
python main.py --check
.\start.ps1
```

启动脚本通过预检后会打开 `http://127.0.0.1:7860/`。如果不想使用脚本，也可以运行：

```powershell
python main.py
```

更完整的安装、配置和排错说明见 [docs/RUNNING.md](docs/RUNNING.md)。

## 可选：启用 Ollama

```powershell
ollama serve
ollama pull qwen2.5:3b
python main.py
```

模型、服务地址、超时、流式输出和驻留时间都可以在 `config.yaml` 的 `brain` 节中调整。

## 如何使用

1. 允许浏览器访问摄像头，保持自然表情片刻，让系统建立会话内基线。
2. 输入文字或提交录音，观察各模态怎样改变当前状态。
3. 展开派生证据，检查真正参与融合的线索和置信度。
4. 使用纠正按钮标记结果是否准确，或者让系统暂时不要判断。
5. 需要重新开始时清空当前会话。

## 评估

仓库带有一组确定性的冲突场景，用于检查融合、冲突检测和报告流程。它们是工程回归样本，
不是受试者数据，也不能用来宣称真实人群上的识别准确率。

```powershell
python scripts\replay_scenarios.py `
  --dataset evaluation\datasets\scripted_conflicts.jsonl `
  --config config.yaml `
  --split scripted `
  --output reports\evaluation\runs\scripted\predictions.jsonl

python scripts\evaluate_sessions.py `
  --predictions reports\evaluation\runs\scripted\predictions.jsonl `
  --output reports\evaluation\runs\scripted-report
```

仓库中的 `reports/evaluation/scripted-final/` 是这组脚本场景的参考输出。真人样本采集、
匿名分组和 dev/test 隔离方法见 [evaluation/README.md](evaluation/README.md)；仓库不附带任何
真人样本或原始媒体。

## 验证开发环境

安装开发依赖后运行：

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check src scripts tests main.py
python main.py --check
```

单元测试和脚本回归不需要摄像头、麦克风、Ollama 或 Whisper 模型。

## 代码结构

```text
src/sentientbot/
├── affect/       # 校准、时序跟踪、融合与响应策略
├── dialogue/     # Ollama 和本机语音播报
├── evaluation/   # 数据校验、回放、指标、搜索与报告
├── perception/   # 面部、文本、ASR 与语音韵律分析
├── storage/      # 隐私约束下的派生事件日志
├── ui/           # Gradio 界面
├── app.py        # 应用编排与降级处理
├── config.py     # 配置模型
├── models.py     # 领域数据结构
└── session.py    # 会话状态
```

内部包名 `sentientbot` 沿用了早期原型，项目和发行名称统一为 EmotiWeave。详细模块关系见
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 已知边界

- 表情和韵律会受到个体、文化、光照、角度、麦克风与环境噪声影响。
- 文本分析采用可解释规则，不等同于完整的语义理解。
- 当前应用按本机单用户场景设计，没有公网服务所需的认证和会话隔离。
- 使用者的自述和纠正始终比系统估计更可靠。

## 许可证

本项目采用 [GNU Affero General Public License v3.0 only](LICENSE)，SPDX 标识为
`AGPL-3.0-only`。通过网络提供修改版服务时，也需要按照许可证提供对应源代码。
