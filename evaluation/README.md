# 情绪识别评估

这个目录包含两类用途不同的数据定义：仓库自带的确定性脚本场景，以及由使用者自行采集、
不会提交到仓库的真人样本。二者在报告中分开统计。

## 可直接复现的脚本回归

`datasets/scripted_conflicts.jsonl` 使用预先构造的 `evidence_override`，验证融合权重、离散
标签、Unknown 状态和三类模态冲突。它不读取摄像头或录音，也不衡量真实人群上的情绪
识别能力。

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

`reports/evaluation/scripted-final/` 保存了一次参考输出。指标只说明给定派生证据下的工程
行为是否稳定，不能写成真人准确率。

## 可选的真人样本评估

真人评估需要单独取得知情同意并自行采集数据。仓库不附带 `data/evaluation/manifest.jsonl`、
参与者记录或原始媒体；`datasets/example_manifest.jsonl` 仅展示字段格式，不是真实样本。

数据集使用 JSONL，每行一个样本：

- `consent_recorded` 必须为 `true`；
- `participant_group` 使用匿名分组，不应包含姓名、邮箱等身份信息；
- 至少提供文本、视频或音频中的一种输入；
- `target.valence` 与 `target.arousal` 范围为 `[-1, 1]`；
- `target.label` 为 `neutral`、`calm`、`positive`、`excited`、`low` 或 `tense`；
- 同一参与者不能同时出现在 dev 与 test 中。

原始视频和 WAV 文件放在 `data/evaluation/media/`，该目录已被 Git 忽略。manifest 只保存
相对路径、必要转写、自述标签和派生所需的最小字段。

采集一条记录：

```powershell
python scripts\collect_evaluation_sample.py `
  --manifest data\evaluation\manifest.jsonl `
  --scenario-id p001-positive-01 `
  --split dev `
  --participant-group participant-001 `
  --label positive `
  --valence 0.70 `
  --arousal 0.30 `
  --transcript "今天很开心" `
  --video media/p001-positive-01.mp4 `
  --audio media/p001-positive-01.wav `
  --consent-recorded
```

校验本地 manifest：

```powershell
python scripts\collect_evaluation_sample.py --validate data\evaluation\manifest.jsonl
```

采集过程中 manifest 可以暂时只有一个 split。冻结评估前，应使用严格校验确认 dev、test
和 scripted 三个 split 都存在，并确认匿名参与者分组没有跨 dev/test 泄漏。
