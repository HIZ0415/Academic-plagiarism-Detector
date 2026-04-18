部署在一个含有 CUDA GPU 的服务器，并启动 AI 推理服务。

## HTTP 联调方式（推荐）

当前已提供一个 HTTP 协议桩服务，用于先打通后端与 AI 端接口。该服务不依赖真实模型，会按协议返回合法的占位检测结果，方便后端和 AI 模型端并行开发。

在 AI 服务目录启动：

```shell
cd 代码/AI服务/AI服务器代码
python ai_http_service.py --host 0.0.0.0 --port 8010
```

健康检查：

```text
GET http://<AI服务器地址>:8010/health
```

图像批量检测接口：

```text
POST http://<AI服务器地址>:8010/api/v1/image-detection/batches
```

如果需要简单鉴权，可在 AI 服务和后端同时设置：

```shell
AI_SERVICE_API_TOKEN=your-token
```

后端启用 HTTP AI 服务时设置：

```shell
AI_SERVICE_URL=http://<AI服务器地址>:8010
AI_SERVICE_TIMEOUT=1200
AI_SERVICE_API_TOKEN=your-token
```

如果后端不设置 `AI_SERVICE_URL`，会继续使用原有 SSH/SCP 方式。

## 旧版 SSH 方式

旧方式为：提供 SSH 连接方式给后端，由后端启动远程 `trigger.py` 进程并传输 `img.zip`、`data.json`。该方式仍保留用于兼容旧部署，但后续联调建议优先使用 HTTP 接口。
