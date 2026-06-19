# 当前项目 API 文档

## 1. 文档说明

本文档是课程组交付版接口文档，依据当前代码中的路由、模型和 AI 服务实现整理。

接口分为两类：

| 类型 | 前缀/地址 | 调用方 |
|---|---|---|
| Django 业务接口 | `/api/` | 用户端前端、管理端前端 |
| WebSocket 通知 | `/ws/notifications/` | 用户端前端、管理端前端 |
| AI 服务接口 | 默认 `http://127.0.0.1:8010` | Django 后端 |

除注册、登录、密码重置等公开接口外，业务接口默认需要 JWT：

```http
Authorization: Bearer <access_token>
```

## 2. 用户认证与账号

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/register/` | 用户注册，邀请码决定发布者或审稿人角色 |
| POST | `/api/login/` | 用户端登录，需提交邮箱、密码和角色 |
| POST | `/api/admin-login/` | 管理端登录，要求用户角色为 `admin` |
| POST | `/api/logout/` | 用户登出 |
| POST | `/api/token/refresh/` | 刷新 JWT |
| GET | `/api/user/details/` | 获取当前用户详情 |
| PUT | `/api/user/update/` | 更新当前用户资料 |
| PUT | `/api/user/avatar/` | 更新头像 |
| POST | `/api/password-reset/` | 请求密码重置验证码 |
| POST | `/api/password-reset/confirm/` | 验证验证码并重置密码 |
| GET | `/api/admin/details/` | 获取当前管理员详情 |
| GET | `/api/admin/details/<user_id>` | 管理端获取指定用户详情 |

## 3. 用户任务、配额与个人记录

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/user-tasks/` | 当前用户检测任务列表 |
| GET | `/api/tasks/<task_id>/detail/` | 统一任务详情 |
| GET | `/api/detection-task/<task_id>/status/` | 用户端查询检测任务状态 |
| DELETE | `/api/detection-task-delete/<task_id>/` | 删除检测任务 |
| GET | `/api/task-summary/` | 当前用户任务摘要 |
| GET | `/api/get-task-summary/` | 任务汇总兼容接口 |
| GET | `/api/organization/usage/` | 查询组织剩余检测额度 |
| POST | `/api/organization/recharge-uses/` | 补充组织检测次数 |
| GET | `/api/single-user-action-log/` | 当前用户操作日志 |
| GET | `/api/reviewer/tasks/` | 审稿人任务列表扩展接口 |
| GET | `/api/reviewer/activity_logs/` | 审稿人活动日志 |

## 4. 文件上传与资源管理

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/upload/` | 上传图片、PDF、压缩包等资源 |
| GET | `/api/upload/<file_id>/` | 获取上传文件详情 |
| GET | `/api/upload/<file_id>/extract_images/` | 获取文件中提取的图片 |
| POST | `/api/upload/<file_id>/addTag/` | 更新文件标签 |
| DELETE | `/api/upload/<file_id>/delete/` | 删除上传文件 |
| GET | `/api/upload/get_all_file_images/<file_management_id>/` | 获取某文件对应的全部图片 |
| GET | `/api/get_files/` | 管理端获取文件列表 |
| DELETE | `/api/delete_image_upload/<image_id>/` | 管理端删除图片记录 |

## 5. 图像检测接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/detection/submit/` | 提交图像检测任务 |
| GET | `/api/detection/<image_id>/` | 获取单张图片检测结果 |
| GET | `/api/tasks/<task_id>/results/` | 获取任务全部检测结果 |
| GET | `/api/tasks/<task_id>/fake_results/` | 获取任务中判定异常的结果 |
| GET | `/api/tasks/<task_id>/normal_results/` | 获取任务中判定正常的结果 |
| GET | `/api/results/<result_id>/` | 获取单条检测结果详情 |
| GET | `/api/results_image/<image_id>/` | 按图片获取检测结果 |
| GET | `/api/tasks_image/<image_id>/getdr/` | 按图片获取检测结果映射 |
| GET | `/api/tasks/<task_id>/report/` | 下载任务级检测报告 |
| GET | `/api/tasks_image/<image_id>/report/` | 下载图片级检测报告 |
| GET | `/api/tasks/<task_id>/comprehensive-report/` | 获取综合鉴伪报告数据 |
| GET | `/api/tasks/<task_id>/comprehensive-report/download/` | 下载综合鉴伪报告 |
| POST | `/api/batch-fusion/` | 多模态批量融合 |

图像检测提交参数包含检测模式、图片列表、任务名称、块大小、URN 参数和是否使用 LLM 等字段。检测结果包含总体真假判断、置信度、子方法结果、mask、EXIF、ELA、LLM 辅助信息等。

## 6. 论文检测与 Review 检测

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/paper/upload/` | 上传论文 PDF 并完成文本预处理 |
| POST | `/api/paper/aigc/submit/` | 提交论文 AIGC 检测任务 |
| GET | `/api/paper/tasks/<task_id>/status/` | 查询论文任务状态 |
| GET | `/api/paper/aigc/<task_id>/result/` | 查询论文 AIGC 检测结果 |
| POST | `/api/paper/resource-check/submit/` | 提交学术资源规范性检查任务 |
| GET | `/api/paper/resource-check/<task_id>/result/` | 查询资源检查结果 |
| POST | `/api/review/submit/` | 提交 Review 文本检测任务 |
| GET | `/api/review/tasks/<task_id>/status/` | 查询 Review 检测任务状态 |
| GET | `/api/review/tasks/<task_id>/result/` | 查询 Review 检测结果 |

约束：

- 论文检测仅支持 `.pdf`。
- Review 检测支持在线文本或 `.txt` 文件。
- 后端会生成 `paper-preprocess-v1` 或 `review-preprocess-v1` AI 输入。

## 7. 人工审核接口

### 7.1 发布者侧

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/manual-review-requests/` | 创建人工审核申请 |
| GET | `/api/manual-review-requests/by-detection-task/` | 按检测任务查询人工审核申请 |
| GET | `/api/manual-review-requests/<review_request_id>/publisher-summary/` | 发布者查看人工审核汇总 |
| POST | `/api/manual-review-requests/<review_request_id>/cancel/` | 发布者取消人工审核申请 |
| GET | `/api/get_publisher_review_tasks/` | 发布者查看自己发起的审核申请列表 |
| GET | `/api/get_request_completion_status/<task_id>/` | 查询审核完成度 |
| GET | `/api/manual-review/<review_id>/report/` | 下载人工审核报告 |

### 7.2 审稿人侧

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/get_reviewer_tasks/` | 审稿人获取待处理人工审核任务 |
| GET | `/api/get_review_detail/<manual_review_id>/` | 审稿人查看人工审核任务详情 |
| POST | `/api/post_review/<manual_review_id>/` | 审稿人提交七项评分、理由和最终结论 |
| GET | `/api/get-reviewer-request-detail/<reviewRequest_id>/` | 审稿人查看审核申请详情 |
| GET | `/api/reviewer-manualreview-access/` | 检查审稿人是否可访问人工审核记录 |

### 7.3 管理员审批

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/get_reviewRequest/all/` | 管理端获取人工审核申请列表 |
| GET | `/api/get_reviewRequest/<reviewRequest_id>/` | 管理端获取审核申请详情 |
| POST | `/api/handle_reviewRequest/<reviewRequest_id>/` | 管理员审批审核申请 |
| DELETE | `/api/review-requests/<review_request_id>/delete/` | 管理员删除审核申请 |

### 7.4 旧页面兼容查询

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/publishers/<publisher_id>/reviewers/` | 获取发布者关联的审稿人 |
| POST | `/api/create_review_task_with_admin_check/` | 创建人工审核申请兼容接口 |
| GET | `/api/get_request_detail/<reviewRequest_id>/` | 获取审核申请详情 |
| GET | `/api/get_img_review_all/` | 获取某图全部审稿人结论 |
| GET | `/api/get_image_review/` | 获取某图某审稿人详情 |
| GET | `/api/manual-review/<review_request_id>/` | 通过审核申请获取人工审核记录 |
| GET | `/api/publisher-dectectiontask-access/` | 检查发布者是否可访问检测任务 |

## 8. 反馈、举报与社区反馈

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/feedback/` | 对人工审核结果点赞或评论 |
| GET | `/api/feedback/<manual_review_id>/` | 获取人工审核结果反馈列表 |
| POST | `/api/reports/submit/` | 用户提交举报 |
| GET | `/api/reports/admin/` | 管理端查看举报列表 |
| POST | `/api/reports/admin/<report_id>/handle/` | 管理员处理举报 |
| GET | `/api/community-feedback/` | 社区反馈流 |

## 9. 通知接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/notification/get/` | 获取通知列表 |
| GET | `/api/notification/notify/` | 获取未读通知数量 |
| POST | `/api/notification/set_as_read/` | 全部标记为已读 |
| POST | `/api/notification/set_as_read/<notification_id>/` | 单条标记为已读 |
| POST | `/api/notification/broadcast/` | 管理员广播通知 |
| WebSocket | `/ws/notifications/` | 实时通知通道 |

## 10. 组织管理接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/organization/create/` | 提交组织申请 |
| GET | `/api/organization/applications/get_pending/` | 获取待审批组织申请 |
| GET | `/api/organization/applications/<app_id>/` | 获取组织申请详情 |
| POST | `/api/organization/<app_id>/approve/` | 批准组织申请 |
| POST | `/api/organization/<app_id>/reject/` | 拒绝组织申请 |
| POST | `/api/organizations/create-directly/` | 管理端直接创建组织 |
| GET | `/api/organizations/` | 获取组织列表 |
| GET | `/api/organization/<org_id>/` | 获取组织详情 |
| DELETE | `/api/organization/<org_id>/delete/` | 删除组织 |
| POST | `/api/organization/<org_id>/permission/` | 更新组织角色权限 |
| GET | `/api/organization/<org_id>/invitation_codes/` | 获取组织邀请码 |
| POST | `/api/organization/upload_logo/` | 上传组织 logo |

## 11. 管理端用户、任务、日志与统计

### 11.1 用户与权限

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/get_users/` | 获取用户列表 |
| POST | `/api/create_user/` | 创建用户 |
| PUT | `/api/update_user/<user_id>/` | 更新用户 |
| DELETE | `/api/delete_user/<user_id>/` | 删除用户 |
| POST | `/api/create-admin/` | 创建管理员 |
| POST | `/api/user_permission/<user_id>/` | 更新用户权限 |
| POST | `/api/manage-associations/` | 建立发布者和审稿人关联 |

### 11.2 任务与日志

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/get_task_summary/` | 管理端任务汇总 |
| GET | `/api/get_detection_task_status/<task_id>/` | 管理端查看检测任务状态 |
| GET | `/api/get_all_user_tasks/` | 管理端查看所有用户任务 |
| GET | `/api/user_action_log/` | 获取用户操作日志 |
| DELETE | `/api/user_action_log/<log_id>/` | 删除日志 |
| GET | `/api/user_action_log/download/` | 导出日志 |
| POST | `/api/post_report/<post_id>/` | 帖子举报处理兼容接口 |

### 11.3 统计看板

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin_dashboard/` | 管理端首页汇总 |
| GET | `/api/dashboard/img_tag/` | 图像标签统计 |
| GET | `/api/dashboard/top_publishers/` | 发布者排行 |
| GET | `/api/dashboard/top_organizations/` | 组织排行 |
| GET | `/api/dashboard/daily_active_users/` | 日活用户统计 |
| GET | `/api/dashboard/daily_active_organizations/` | 日活组织统计 |
| GET | `/api/dashboard/daily_task_count/` | 每日任务数量 |
| GET | `/api/dashboard/daily_review_request_count/` | 每日审核申请数量 |
| GET | `/api/dashboard/daily_completed_manual_review_count/` | 每日完成人工审核数量 |
| GET | `/api/dashboard/get_sub_method_distribution_by_tag/` | 按标签统计子方法分布 |

## 12. 检测模型配置

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/detection-models/` | 获取检测模型目录 |
| POST | `/api/detection-preferences/` | 更新用户检测偏好 |
| GET/POST | `/api/admin/detection-models/` | 管理端查看或更新检测模型配置 |
| GET | `/api/admin/detection-logs/` | 管理端查看检测日志 |

## 13. AI 服务接口

AI 服务默认本地地址：

```text
http://127.0.0.1:8010
```

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查，返回服务状态、任务类型、模型 profile 等 |
| POST | `/api/v1/image-detection/batches` | 图像批量检测主接口 |
| POST | `/api/v1/detection/batches` | 通用检测兼容入口 |
| POST | `/api/v1/paper-detection/batches` | 论文检测扩展入口 |
| POST | `/api/v1/review-detection/batches` | Review 检测扩展入口 |
| GET | `/api/v1/admin/model-registry` | 查询模型注册表和 profile |

如设置了 `AI_SERVICE_API_TOKEN`，调用 AI 服务需携带：

```http
Authorization: Bearer <AI_SERVICE_API_TOKEN>
```

### 13.1 后端到 AI 的请求结构

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
    "model_profile": "minimal_trainable"
  },
  "image_names": ["00000123.jpg"],
  "images_zip_base64": "base64 encoded zip bytes"
}
```

### 13.2 AI 服务错误结构

```json
{
  "schema_version": "ai-service-error-v1",
  "error_code": "validation_error",
  "error_type": "ValidationError",
  "message": "unsupported schema_version",
  "status": 400,
  "retriable": false,
  "task_type": "image",
  "batch_id": "task_1_batch_0",
  "details": {}
}
```

## 14. 任务类型与状态

### 14.1 任务类型

| 值 | 说明 |
|---|---|
| `image_detection` | 图像检测 |
| `paper_aigc` | 论文 AIGC 检测 |
| `resource_check` | 学术资源规范性检查 |
| `review_detection` | Review 文本检测 |

### 14.2 任务状态

| 值 | 说明 |
|---|---|
| `pending` | 待处理 |
| `in_progress` | 处理中 |
| `completed` | 已完成 |
| `failed` | 失败 |

### 14.3 人工审核状态

| 字段 | 值 | 说明 |
|---|---|---|
| `ReviewRequest.status2` | `pending` / `accepted` / `refused` | 管理员审批状态 |
| `ReviewRequest.status1` | `pending` / `in_progress` / `completed` | 审核流程状态 |
| `ManualReview.status` | `undo` / `completed` | 审稿人任务状态 |
