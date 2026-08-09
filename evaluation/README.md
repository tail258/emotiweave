# 情绪识别评估数据

数据集采用 JSONL，每行一个样本。参与者样本必须有 `consent_recorded: true`、匿名的 `participant_group` 和至少一个输入模态。`target.valence` 与 `target.arousal` 使用 `[-1, 1]`，`target.label` 使用 `neutral`、`calm`、`positive`、`excited`、`low`、`tense`。

原始视频和 WAV 文件放在 `data/evaluation/media/`，不提交到 Git。manifest 只保存相对路径、转写文本、参与者自述标签和派生结果所需的最小字段。脚本样本使用 `split: scripted` 与 `evidence_override`，不能和参与者准确率混合统计。

采集命令示例：

```powershell
py -3.11 scripts/collect_evaluation_sample.py `
  --manifest data/evaluation/manifest.jsonl `
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

校验命令：

```powershell
py -3.11 scripts/collect_evaluation_sample.py --validate data/evaluation/manifest.jsonl
```

追加样本时允许 manifest 暂时只有一个 split；最终冻结测试集前，严格校验要求同时存在 `dev`、`test` 和 `scripted` 三个 split，并检查参与者分组没有跨 dev/test 泄漏。
