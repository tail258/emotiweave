# EmotiWeave｜情绪织谱参赛提交包

本文件夹集中存放外滩黑客松提交所需的说明材料与人工操作指南。应用源码仍以项目根目录
中的原文件为唯一版本，不在此处重复复制。

## 推荐阅读和操作顺序

1. [赛方表单填写内容](01-form-content.md)：复制作品描述并确认元信息。
2. [项目运行说明](02-project-runbook.md)：可直接上传到“项目运行说明文档”字段。
3. [公开源码清单](03-source-manifest.md)：确认 GitHub 应包含和排除哪些文件。
4. [GitHub 与 ModelScope 发布指南](04-github-and-modelscope-guide.md)：按顺序完成公开发布。
5. [图片准备清单](05-image-checklist.md)：准备封面和真实界面快照。
6. [最终提交检查表](06-final-submission-checklist.md)：提交前逐项确认。
7. [图片存放规则](assets/README.md)：生成的封面和快照统一放入 `submission/assets/`。

## 当前状态

已经具备：

- 可运行的本地项目；
- 情绪识别评估、脚本回放和报告工具；
- 经过验证的测试基线；
- 作品描述、运行说明、源码路径和人工提交步骤。

尚需完成：

- 按公网部署设计实施 ModelScope 适配；
- 建立公开 GitHub 仓库；
- 发布并验收 ModelScope 创空间；
- 截取真实运行界面；
- 将最终 URL 和图片提交到赛方表单。

GitHub 和 ModelScope 的实际 URL 只有在你完成公开发布后才会产生。不要把本机地址
`http://127.0.0.1:7860/` 或会过期的 `gradio.live` 临时地址填写为正式作品链接。

## 本地位置

- 提交包：`D:\工作区\SentientBot_V2\submission`
- 项目源码：`D:\工作区\SentientBot_V2`
- 公网部署设计：
  `D:\工作区\SentientBot_V2\docs\superpowers\specs\2026-08-09-public-submission-link-design.md`
