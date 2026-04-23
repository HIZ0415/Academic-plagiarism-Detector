# 论文AIGC与学术资源检测接口契约（并行开发版）

## 1. 目标与范围

本契约用于支撑以下迭代目标：

- 建立论文检测相关数据库结构
- 用户端实现论文文件上传
- 用户端实现全篇论文 AIGC 检测
- 用户端实现同行评审 Review 相关链路对接
- 用户端实现学术资源检测

说明：

- 当前项目已有图像检测与人工审核流程，本契约优先复用既有任务状态设计
- 本文档聚焦“接口结构冻结”，便于两人并行开发，避免覆盖

---

## 2. 统一约定

### 2.1 基础路径

- 所有接口统一挂载在：`/api/`

### 2.2 认证

- 需要登录的接口必须带：`Authorization: Bearer <access_token>`

### 2.3 通用任务状态

- `pending`
- `in_progress`
- `completed`
- `failed`

### 2.4 统一时间格式

- 使用 ISO 8601 字符串，如：`2026-04-20T17:12:00+08:00`

### 2.5 论文格式

- 本迭代最低支持：`pdf`、`docx`、`txt`
- 可选扩展：`zip`、`rar`（仅当明确实现解包）

---

## 3. 数据库最小模型（后端必须先落地）

## 3.1 PaperFile（论文文件元数据）

- `id`：主键
- `user_id`：上传用户
- `organization_id`：所属组织（可空）
- `file_name`：原文件名
- `file_type`：MIME 或扩展名
- `file_size`：大小（字节）
- `storage_path`：存储路径
- `upload_time`：上传时间

## 3.2 PaperDetectionTask（论文检测任务）

- `id`：主键
- `user_id`：任务所属用户
- `organization_id`：所属组织（可空）
- `paper_file_id`：关联 `PaperFile`
- `task_type`：`paper_aigc` / `resource_check`
- `task_name`：任务名
- `status`：任务状态（见 2.3）
- `upload_time`：创建时间
- `completion_time`：完成时间（可空）
- `error_message`：失败原因（可空）

## 3.3 PaperAigcResult（全篇AIGC结果）

- `id`：主键
- `task_id`：关联 `PaperDetectionTask`
- `overall_risk_level`：`low` / `medium` / `high`
- `ai_contribution_ratio`：0~1
- `summary`：全文摘要结论
- `paragraph_count`：段落总数
- `high_risk_count`：高风险段落数
- `result_json`：段落级详情（JSON）
- `updated_at`：更新时间

## 3.4 ResourceCheckResult（学术资源检测结果）

- `id`：主键
- `task_id`：关联 `PaperDetectionTask`
- `total_references`：参考文献总数
- `doi_found_count`：识别到 DOI 数
- `doi_invalid_count`：无效 DOI 数
- `suspected_risk_count`：可疑资源条目数
- `summary`：检测摘要
- `issues_json`：问题明细（JSON）
- `updated_at`：更新时间

---

## 4. 接口定义（冻结）

## 4.1 上传论文文件

- **URL**：`POST /api/paper/upload/`
- **鉴权**：是
- **Content-Type**：`multipart/form-data`
- **字段**：
  - `file`：论文文件（pdf/docx/txt）
  - `task_name`（可选）

### 成功响应（200）

```json
{
  "message": "Paper uploaded successfully",
  "paper_file_id": 101,
  "file_name": "demo-paper.pdf",
  "upload_time": "2026-04-20T17:12:00+08:00"
}
```

### 失败响应（400/403）

```json
{
  "message": "Invalid file type. only pdf/docx/txt are allowed."
}
```

## 4.2 提交全篇论文AIGC检测任务

- **URL**：`POST /api/paper/aigc/submit/`
- **鉴权**：是
- **Body**：

```json
{
  "paper_file_id": 101,
  "task_name": "论文AIGC检测-示例"
}
```

### 成功响应（200）

```json
{
  "message": "Paper AIGC task submitted successfully",
  "task_id": 8801,
  "task_type": "paper_aigc",
  "status": "pending"
}
```

## 4.3 查询任务状态（通用）

- **URL**：`GET /api/paper/tasks/<task_id>/status/`
- **鉴权**：是

### 成功响应（200）

```json
{
  "task_id": 8801,
  "task_type": "paper_aigc",
  "task_name": "论文AIGC检测-示例",
  "status": "in_progress",
  "upload_time": "2026-04-20T17:12:30+08:00",
  "completion_time": null,
  "error_message": null
}
```

## 4.4 获取全篇AIGC结果

- **URL**：`GET /api/paper/aigc/<task_id>/result/`
- **鉴权**：是
- **前提**：任务已 `completed`

### 成功响应（200）

```json
{
  "task_id": 8801,
  "overall_risk_level": "medium",
  "ai_contribution_ratio": 0.42,
  "summary": "全文存在中等AI生成风险，建议重点复核高风险段落。",
  "paragraph_count": 36,
  "high_risk_count": 7,
  "paragraphs": [
    {
      "index": 5,
      "risk_score": 0.81,
      "risk_level": "high",
      "excerpt": "......"
    }
  ],
  "updated_at": "2026-04-20T17:13:58+08:00"
}
```

### 失败响应（202/404）

```json
{
  "message": "Task not completed yet"
}
```

## 4.5 提交学术资源检测任务

- **URL**：`POST /api/paper/resource-check/submit/`
- **鉴权**：是
- **Body**：

```json
{
  "paper_file_id": 101,
  "task_name": "学术资源检测-示例"
}
```

### 成功响应（200）

```json
{
  "message": "Resource check task submitted successfully",
  "task_id": 9901,
  "task_type": "resource_check",
  "status": "pending"
}
```

## 4.6 获取学术资源检测结果

- **URL**：`GET /api/paper/resource-check/<task_id>/result/`
- **鉴权**：是
- **前提**：任务已 `completed`

### 成功响应（200）

```json
{
  "task_id": 9901,
  "total_references": 28,
  "doi_found_count": 20,
  "doi_invalid_count": 3,
  "suspected_risk_count": 4,
  "summary": "发现 3 条 DOI 无效，4 条参考文献存在来源可疑风险。",
  "issues": [
    {
      "index": 2,
      "type": "invalid_doi",
      "detail": "10.1234/abcd is not resolvable"
    }
  ],
  "updated_at": "2026-04-20T17:16:20+08:00"
}
```

---

## 5. 与既有 Review 功能的接口关系

- 现有 `ReviewRequest` / `ManualReview` 链路继续可用
- 新增论文检测任务后，允许在前端“检测结果页”发起已有人工审核流程
- 本迭代不强制重构旧 Review 表，只做对接入口

---

## 6. 两人并行分工（防覆盖）

## 6.1 人员A（你）：接口契约与联调层

只改：

- `代码/后端/后端代码/core/urls.py`
- `文档/APIs/*.md`
- `代码/前端/前端用户端/src/api/*`

负责：

- 新接口路径接入
- 请求/响应字段与前端对齐
- 联调记录、错误清单

## 6.2 人员B（队友）：数据层与任务执行层

只改：

- `代码/后端/后端代码/core/models.py`
- `代码/后端/后端代码/core/views/views_*.py`（新增 paper/resource）
- `代码/后端/后端代码/core/tasks*.py`
- migrations

负责：

- 表结构与迁移
- 任务创建、状态推进、结果落库
- Celery 执行链路

---

## 7. 本周落地节奏（D1~D5）

- **D1**：冻结接口字段 + 建最小模型 + 迁移
- **D2**：打通上传接口 + AIGC任务提交 + 状态查询
- **D3**：打通AIGC结果接口（可先mock）
- **D4**：打通资源检测任务与结果（可先mock）
- **D5**：前后端联调 + 文档补齐 + 演示脚本

---

## 8. 联调验收清单（最小通过标准）

- 上传论文后返回 `paper_file_id`
- 能提交 AIGC 任务并拿到 `task_id`
- 任务状态能从 `pending -> in_progress -> completed`
- 能拿到 AIGC 结构化结果（含全文结论和段落风险）
- 能提交资源检测任务并获取问题列表
- 现有 Review 功能不回归、不受影响

