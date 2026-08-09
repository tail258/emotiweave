# GitHub 公开源码清单

项目根目录：`D:\工作区\SentientBot_V2`

本清单是公开 GitHub 仓库的文件范围依据。不要整体复制工作区，也不要使用不经检查的
`git add .`。

## 必须公开

| 内容 | 本机绝对路径 | GitHub 仓库路径 |
|---|---|---|
| 应用源码 | `D:\工作区\SentientBot_V2\src\sentientbot` | `src/sentientbot/` |
| 单元测试 | `D:\工作区\SentientBot_V2\tests` | `tests/` |
| 运行与评估脚本 | `D:\工作区\SentientBot_V2\scripts` | `scripts/` |
| 评估说明与脚本数据 | `D:\工作区\SentientBot_V2\evaluation` | `evaluation/` |
| 模型目录占位文件 | `D:\工作区\SentientBot_V2\assets\models\.gitkeep` | `assets/models/.gitkeep` |
| 主入口 | `D:\工作区\SentientBot_V2\main.py` | `main.py` |
| Windows 启动脚本 | `D:\工作区\SentientBot_V2\start.ps1` | `start.ps1` |
| 默认配置 | `D:\工作区\SentientBot_V2\config.yaml` | `config.yaml` |
| Python 项目配置 | `D:\工作区\SentientBot_V2\pyproject.toml` | `pyproject.toml` |
| 依赖文件 | `D:\工作区\SentientBot_V2\requirements.txt` | `requirements.txt` |
| 项目主页 | `D:\工作区\SentientBot_V2\README.md` | `README.md` |
| 忽略规则 | `D:\工作区\SentientBot_V2\.gitignore` | `.gitignore` |
| 架构文档 | `D:\工作区\SentientBot_V2\docs\ARCHITECTURE.md` | `docs/ARCHITECTURE.md` |
| 参赛提交包 | `D:\工作区\SentientBot_V2\submission` | `submission/` |

## 可以公开的精简工程回归报告

只建议公开下列文件：

| 本机绝对路径 | GitHub 仓库路径 |
|---|---|
| `D:\工作区\SentientBot_V2\reports\evaluation\scripted-final\metrics.md` | `reports/evaluation/scripted-final/metrics.md` |
| `D:\工作区\SentientBot_V2\reports\evaluation\scripted-final\summary.json` | `reports/evaluation/scripted-final/summary.json` |
| `D:\工作区\SentientBot_V2\reports\evaluation\scripted-final\confusion_matrix.csv` | `reports/evaluation/scripted-final/confusion_matrix.csv` |
| `D:\工作区\SentientBot_V2\reports\evaluation\scripted-final\per_sample.csv` | `reports/evaluation/scripted-final/per_sample.csv` |

这些结果是确定性脚本场景的工程回归材料，不是真实参与者准确率。不要把调参目录中的单样本
搜索结果当作最终配置依据。

## 暂不公开

| 路径或类型 | 原因 |
|---|---|
| `.venv/`、`venv/` | 本机虚拟环境，体积大且不可移植 |
| `__pycache__/`、`*.pyc`、`.pytest_cache/`、`.ruff_cache/` | 缓存和字节码 |
| `.agents/` | 本机代理配置，与作品运行无关 |
| `.codex-output/` | 本机调试日志和临时截图 |
| `.git/` | 仓库内部元数据，不作为普通文件上传 |
| `data/sessions/` | 会话日志 |
| `data/evaluation/media/` | 参与者原始媒体，涉及隐私 |
| `data/evaluation/manifest.jsonl` | 可能包含参与者和本机媒体路径 |
| `data/note-backups/` | 开发笔记备份，与提交运行无关 |
| `reports/evaluation/runs/` | 预测中间文件 |
| `reports/**/*.html` | Plotly 自包含文件体积很大，不是必要源码 |
| `reports/evaluation/tuning/` | 当前只是示例样本调参结果，不能当作正式结论 |
| `core/`、`drivers/`、`utils/` | 当前只剩旧版字节码缓存，没有可公开源文件 |
| `assets/models/*.task` | 本机下载的模型二进制；公开版通过脚本获取 |
| `.env`、令牌、Cookie、SSH 密钥、平台配置密钥 | 敏感凭据，严禁提交 |

## 发布前检查

在项目根目录执行：

```powershell
git status --short
git diff --cached --stat
git diff --cached --name-only
```

逐行确认暂存区只出现本清单允许的路径。尤其检查是否出现 `data/`、`.codex-output/`、
`.agents/`、`.env`、模型二进制或个人媒体文件。

## 许可证说明

项目采用 GNU Affero General Public License v3.0 only，SPDX 标识为
`AGPL-3.0-only`。完整条款见仓库根目录的 `LICENSE`；部署修改版网络服务时，应同时核对
许可证关于向网络用户提供对应源代码的要求。
