# AI 模型迭代开发接口契约

## 1. 目标

本文档约定 AI 推理服务与后端任务系统之间的数据契约，用于支撑后续图像检测模型替换、论文检测模型接入和 Review 检测模型接入。

当前后端已经兼容两种输出：

- 旧版输出：`trigger.py` 通过 `pickle + base64` 输出的 tuple/list 结构；
- 新版输出：推荐后续模型迭代使用的 JSON/dict schema。

后端归一化入口为：

```text
代码/后端/后端代码/core/utils/ai_result_schema.py
```

Celery 任务只依赖归一化后的单图结果，不再直接依赖旧 tuple 的位置结构。

## 2. 图像检测输入

后端与 AI 端推荐通过 HTTP JSON 协议通信：

```text
POST /api/v1/image-detection/batches
Content-Type: application/json
Authorization: Bearer <AI_SERVICE_API_TOKEN>  # 可选
```

健康检查接口：

```text
GET /health
```

后端提交给 AI 服务的请求体为：

```json
{
  "schema_version": "backend-ai-request-v1",
  "task_type": "image",
  "batch_id": "task_1_batch_0",
  "parameters": {
    "cmd_block_size": 64,
    "urn_k": 0.3,
    "if_use_llm": false,
    "model_version": "image-detector-2026-04"
  },
  "image_names": ["00000123.jpg"],
  "images_zip_base64": "base64 encoded zip bytes"
}
```

其中 `images_zip_base64` 是后端打包出的图片 ZIP 文件内容。`image_names` 按 ZIP 内图片顺序给出，AI 端返回结果时建议保留对应 `image_name`。

后端内部仍会生成以下两个文件；HTTP 网关会读取它们并组装成上述请求：

```text
test/img.zip
test/data.json
```

`img.zip` 中包含一批待检测图像。后端当前按每批最多 20 张图片打包，文件名形如：

```text
00000123.jpg
00000124.png
```

`data.json` 当前字段如下：

```json
{
  "cmd_block_size": 64,
  "urn_k": 0.3,
  "if_use_llm": false
}
```

后续可扩展字段：

```json
{
  "task_type": "image",
  "model_version": "image-detector-2026-04",
  "threshold": 0.5
}
```

如果后端未配置 `AI_SERVICE_URL`，系统会回退到历史 SSH/SCP 调用方式，以兼容旧部署。

## 3. 图像检测推荐输出

后续推荐 AI 服务直接返回如下结构。若仍通过 `pickle + base64` 传输，也建议 pickle 的对象本身使用该 dict 结构。

```json
{
  "schema_version": "image-detection-v1",
  "task_type": "image",
  "model_version": "image-detector-2026-04",
  "results": [
    {
      "image_name": "00000123.jpg",
      "image_id": 123,
      "overall_is_fake": true,
      "overall_confidence": 0.91,
      "llm_text": "可疑区域集中在图像右下角，存在拼接痕迹。",
      "llm_img": null,
      "ela": [[0, 1, 2]],
      "exif_flags": {
        "photoshop": false,
        "time_modified": false
      },
      "sub_method_results": [
        {
          "method": "splicing",
          "probability": 0.91,
          "mask": [[0.0, 1.0]]
        }
      ]
    }
  ]
}
```

## 4. 单图结果字段说明

| 字段 | 必填 | 说明 |
|---|---:|---|
| `image_name` | 否 | 图像在 `img.zip` 中的文件名。建议填写，便于排查顺序问题。 |
| `image_id` | 否 | 图像业务 ID。当前后端按提交顺序映射，可不填。 |
| `overall_is_fake` | 是 | 总体真假判定，布尔值。 |
| `overall_confidence` | 是 | 总体置信度，建议范围为 `0.0` 到 `1.0`。 |
| `llm_text` | 否 | 大模型解释文本；未启用 LLM 时填 `"无"` 或 `null`。 |
| `llm_img` | 否 | LLM 可视化图像矩阵；没有时填 `null`。 |
| `ela` | 是 | ELA 或主可视化图像矩阵，会保存到 `DetectionResult.ela_image`。 |
| `exif_flags.photoshop` | 是 | 是否检测到 Photoshop 修改痕迹。 |
| `exif_flags.time_modified` | 是 | 是否检测到时间信息修改。 |
| `sub_method_results` | 是 | 子检测方法结果列表。 |
| `sub_method_results[].method` | 是 | 方法名，例如 `splicing`、`blurring`、`bruteforce`、`contrast`、`inpainting`。 |
| `sub_method_results[].probability` | 是 | 子方法概率。后端也兼容字段名 `prob`。 |
| `sub_method_results[].mask` | 是 | 子方法 mask 矩阵，建议使用 `0.0` 到 `1.0`。 |

## 5. 后端落库映射

归一化后的结果会写入以下模型：

| 归一化字段 | 后端字段 |
|---|---|
| `overall_is_fake` | `DetectionResult.is_fake` |
| `overall_confidence` | `DetectionResult.confidence_score` |
| `llm_text` | `DetectionResult.llm_judgment` |
| `llm_img` | `DetectionResult.llm_image` |
| `ela` | `DetectionResult.ela_image` |
| `exif_flags.photoshop` | `DetectionResult.exif_photoshop` |
| `exif_flags.time_modified` | `DetectionResult.exif_time_modified` |
| `sub_method_results[].method` | `SubDetectionResult.method` |
| `sub_method_results[].probability` 或 `prob` | `SubDetectionResult.probability` |
| `sub_method_results[].mask` | `SubDetectionResult.mask_image` 和 `SubDetectionResult.mask_matrix` |

## 6. 论文检测与 Review 检测扩展建议

论文检测和 Review 检测尚未接入当前后端主链路。接入时建议沿用同样的顶层结构：

```json
{
  "schema_version": "paper-detection-v1",
  "task_type": "paper",
  "model_version": "paper-detector-2026-04",
  "results": []
}
```

论文检测的 `results` 建议包含：

- 全文总体 AI 生成概率；
- 段落级 AI 生成概率；
- 可疑段落文本位置；
- 事实性鉴伪子结论；
- 原因说明；
- 模型版本与阈值。

Review 检测的 `results` 建议包含：

- 整体 AI 生成风险；
- 模板化风险评分；
- 可疑句子或短语；
- 相似/模板命中原因；
- 模型版本与阈值。

## 7. 迭代规则

1. 新模型可以改变内部算法，但不要直接改变后端已经消费的字段语义。
2. 如果必须新增字段，优先新增到 schema 中，后端暂时可以忽略。
3. 如果必须删除或重命名字段，需要同步修改 `core/utils/ai_result_schema.py`。
4. 新模型发布时必须填写 `model_version`，便于后续结果追溯和模型对比。
5. 子方法 `method` 名称应保持稳定，否则历史报告和管理端统计会出现口径漂移。
