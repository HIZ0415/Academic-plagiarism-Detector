# AI学术鉴伪系统
## 配置环境
+ python 3.11

## 文件预处理说明

- 论文检测当前只接收 PDF 文件。后端上传后会用 PyMuPDF 提取 PDF 文本，完成文本清洗、段落切分，并生成 `paper-preprocess-v1` AI 输入。
- 专家人工 Review 检测当前只接收在线文本或 `.txt` 文件。后端会完成编码标准化、BOM 清理、控制字符清理和空白归一化，并生成 `review-preprocess-v1` AI 输入。
- 本地后端依赖以 `代码/后端/后端代码/requirements.local.txt` 为准，其中 PDF 预处理需要 `PyMuPDF`。
