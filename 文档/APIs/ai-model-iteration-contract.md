# AI 模型迭代开发接口契约

## 1. 目标

本文档定义当前 AI 服务与后端之间的接口契约，适用于：

- 图像检测主链路
- AI 服务本地最小可运行版本
- 后续 `paper` / `review` 任务扩展

后端当前统一消费的是 JSON/dict 结果；旧的 `pickle + base64 + tuple/list` 方式仍保留兼容入口，但不再推荐继续迭代。

后端归一化入口：

```text
代码/后端/后端代码/core/utils/ai_result_schema.py
```

## 2. HTTP 接口

AI 服务当前开放以下接口：

```text
POST /api/v1/image-detection/batches
GET  /health
GET  /api/v1/admin/model-registry
```

其中：

- `POST /api/v1/image-detection/batches`：图像检测主接口
- `GET /health`：服务健康检查
- `GET /api/v1/admin/model-registry`：只读管理接口，用于查看当前 registry、profile 和重载状态

如配置了 `AI_SERVICE_API_TOKEN`，请求需带：

```text
Authorization: Bearer <AI_SERVICE_API_TOKEN>
```

## 3. 图像检测请求

推荐请求结构如下：

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

- `schema_version`：当前固定为 `backend-ai-request-v1`
- `task_type`：当前主链路支持 `image`
- `batch_id`：建议传入，便于日志与追踪
- `parameters`：检测参数集合
- `parameters.model_version`：可选；不传时由 AI 服务按 profile 自动回填
- `parameters.model_profile`：可选；用于指定模型配置档位
- `image_names`：ZIP 内图片文件名列表
- `images_zip_base64`：图片 ZIP 文件内容的 Base64

后端当前会生成：

```text
test/img.zip
test/data.json
```

AI 服务也保留了从这两个文件组装请求的本地脚本入口。

## 4. 图像检测响应

当前推荐响应结构如下：

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
        },
        {
          "method": "blurring",
          "probability": 0.0,
          "mask": []
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
          "metadata": {
            "model_path": "..."
          }
        }
      ]
    }
  ]
}
```

注意：

- `results` 内保留了后端当前落库所需的兼容字段
- `evidences` 是新的标准化证据对象，后端当前可忽略，但推荐后续使用
- `batch_id` 已贯穿到顶层响应

## 5. 单图结果字段说明

| 字段 | 必填 | 说明 |
|---|---:|---|
| `image_name` | 是 | 图片文件名 |
| `image_id` | 否 | 图片业务 ID；文件名是纯数字时可自动解析 |
| `overall_is_fake` | 是 | 总体真假判定 |
| `overall_confidence` | 是 | 总体置信度，范围建议为 `0.0 ~ 1.0` |
| `llm_text` | 是 | LLM 解释文本；未启用时返回空字符串 |
| `llm_img` | 是 | LLM 可视化结果；无则为 `null` |
| `ela` | 是 | ELA 热图；最小 profile 可为空列表 |
| `exif_flags` | 是 | EXIF 异常标志 |
| `sub_method_results` | 是 | 子检测方法结果列表 |
| `sub_method_results[].method` | 是 | 子方法名 |
| `sub_method_results[].probability` | 是 | 子方法概率；后端也兼容 `prob` |
| `sub_method_results[].mask` | 是 | 子方法 mask |
| `evidences` | 否 | 标准化证据对象列表 |

## 6. 健康检查接口

```text
GET /health
```

当前典型返回如下：

```json
{
  "status": "ok",
  "service_version": "ai-detection-service-2026-04",
  "supported_tasks": ["image"],
  "reserved_tasks": ["paper", "review"],
  "result_format": "standard-evidence-v1",
  "registry_version": "image-model-registry-v1",
  "default_image_profile": "default",
  "available_image_profiles": ["default", "fast", "minimal_trainable"],
  "image_profile_details": {
    "minimal_trainable": {
      "model_version": "image-detector-minimal-2026-04",
      "enabled_methods": ["exif", "splicing"]
    }
  },
  "registry_reload": {
    "reload_count": 0,
    "last_reload_at": null,
    "last_reload_error": null
  }
}
```

## 7. 只读管理接口

```text
GET /api/v1/admin/model-registry
GET /api/v1/admin/model-registry?profile=minimal_trainable
```

用途：

- 查看当前 registry 路径与版本
- 查看默认 profile
- 查看所有可用 profile
- 查看指定 profile 的方法配置
- 查看 registry 热重载状态

该接口为只读接口，不负责在线修改配置。

## 8. `paper` / `review` 预留规则

当前 AI 服务已预留：

- `task_type = "paper"`
- `task_type = "review"`

请求中允许携带：

```json
{
  "payload_base64": "..."
}
```

但当前仅保留路由与错误语义，尚未形成真实检测链路；调用时会返回未实现错误。

## 9. 迭代规则

1. 新模型可以替换内部算法，但不要改变后端已消费字段的语义。
2. 如需扩展能力，优先新增字段，不直接删除旧字段。
3. 新模型发布时必须提供稳定的 `model_version`。
4. 如使用多套模型配置，推荐通过 `model_profile` 选择，并让服务自动回填默认 `model_version`。
5. `sub_method_results[].method` 应保持稳定，避免管理端统计口径漂移。
6. 如新增顶层管理或观测接口，需同步更新本地部署和启动手册。
