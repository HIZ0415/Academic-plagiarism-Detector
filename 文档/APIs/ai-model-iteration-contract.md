# AI 服务接口契约

## 1. 说明

本文档说明 Django 后端与 AI HTTP 服务之间的接口契约。前端不直接调用 AI 服务，所有业务请求均先进入 Django `/api/`。

AI 服务默认本地地址：

```text
http://127.0.0.1:8010
```

## 2. 接口列表

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 服务健康检查 |
| POST | `/api/v1/image-detection/batches` | 图像批量检测主接口 |
| POST | `/api/v1/detection/batches` | 通用检测兼容入口 |
| POST | `/api/v1/paper-detection/batches` | 论文检测扩展入口 |
| POST | `/api/v1/review-detection/batches` | Review 检测扩展入口 |
| GET | `/api/v1/admin/model-registry` | 查询模型注册表和 profile |

如配置 `AI_SERVICE_API_TOKEN`，请求需携带：

```http
Authorization: Bearer <AI_SERVICE_API_TOKEN>
```

## 3. 后端请求结构

```json
{
  "schema_version": "backend-ai-request-v1",
  "task_type": "image",
  "batch_id": "task_1_batch_0",
  "parameters": {
    "cmd_block_size": 64,
    "urn_k": 0.3,
    "if_use_llm": false,
    "threshold": 0.5,
    "model_version": "image-detector-2026-04",
    "model_profile": "minimal_trainable"
  },
  "image_names": ["00000123.jpg"],
  "images_zip_base64": "base64 encoded zip bytes"
}
```

字段说明：

| 字段 | 说明 |
|---|---|
| `schema_version` | 当前固定为 `backend-ai-request-v1` |
| `task_type` | 任务类型，图像主链路为 `image` |
| `batch_id` | 批次标识，便于追踪日志 |
| `parameters` | 检测参数，包括模型版本、profile、阈值等 |
| `image_names` | ZIP 内图片文件名列表 |
| `images_zip_base64` | 图片 ZIP 的 Base64 内容 |

## 4. 图像检测响应结构

```json
{
  "schema_version": "image-detection-v1",
  "task_type": "image",
  "model_version": "image-detector-minimal-2026-04",
  "batch_id": "task_1_batch_0",
  "results": [
    {
      "schema_version": "image-detection-v1",
      "task_type": "image",
      "model_version": "image-detector-minimal-2026-04",
      "image_name": "00000123.jpg",
      "image_id": 123,
      "overall_is_fake": false,
      "overall_confidence": 0.29,
      "llm_text": "",
      "llm_img": null,
      "ela": [],
      "exif_flags": {
        "photoshop": false,
        "time_modified": false
      },
      "sub_method_results": [
        {
          "method": "splicing",
          "probability": 0.29,
          "mask": [[0.0, 0.1]]
        }
      ],
      "evidences": [
        {
          "schema_version": "standard-evidence-v1",
          "evidence_id": "00000123.jpg:splicing",
          "method": "splicing",
          "category": "classification",
          "evidence_type": "score",
          "suspicious": false,
          "confidence": 0.29,
          "summary": "splicing baseline classifier probability: 0.290",
          "artifacts": {
            "mask": [[0.0, 0.1]]
          },
          "metadata": {}
        }
      ]
    }
  ]
}
```

说明：

- `overall_is_fake` 和 `overall_confidence` 用于后端落库和前端展示。
- `sub_method_results` 保存子方法结果和 mask 数据。
- `evidences` 是标准化证据对象，用于后续扩展更统一的解释性结果。

## 5. 文本检测响应结构

论文和 Review 文本检测使用 `text-detection-v1` 结果结构：

```json
{
  "schema_version": "text-detection-v1",
  "task_type": "review",
  "model_version": "review-detector-service-2026-04",
  "source_name": "review.txt",
  "overall_is_fake": false,
  "overall_confidence": 0.31,
  "summary": "文本检测摘要",
  "text_length": 1200,
  "details": {},
  "evidences": []
}
```

## 6. 错误响应结构

```json
{
  "schema_version": "ai-service-error-v1",
  "error_code": "validation_error",
  "error_type": "ValidationError",
  "message": "unsupported schema_version",
  "error": "unsupported schema_version",
  "status": 400,
  "retriable": false,
  "task_type": "image",
  "batch_id": "task_1_batch_0",
  "details": {
    "field": "schema_version"
  }
}
```

常见错误码：

| 错误码 | 说明 |
|---|---|
| `validation_error` | 请求格式或字段不合法 |
| `task_not_implemented` | 请求的任务类型暂未实现 |
| `unauthorized` | AI 服务鉴权失败 |
| `timeout` | 检测超时 |
| `internal_error` | AI 服务内部错误 |
| `not_found` | 路径不存在 |

## 7. 健康检查

`GET /health` 返回服务状态、支持任务、结果格式、默认 profile、可用 profile、热加载状态等信息。课程演示时可用该接口确认 AI 服务已经启动。

## 8. 模型注册表

`GET /api/v1/admin/model-registry` 用于查看当前 AI 服务已加载的 registry、profile 和模型版本。可选查询参数：

| 参数 | 说明 |
|---|---|
| `profile` | 指定后仅查看某个 profile 的详情 |
