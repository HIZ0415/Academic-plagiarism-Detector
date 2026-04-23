# 当前项目 API 文档

## 1. 说明
本文档对应当前仓库中已经落地的接口实现，分为两层：

- 后端对外业务接口：Django 应用，对前端提供统一的 `/api/` 路由。
- AI 服务内部接口：独立 HTTP 服务，供后端调用，不直接挂载在 Django `/api/` 下。

本文档依据以下代码整理：

- 路由入口：`代码/后端/后端代码/fake_image_detector/urls.py`
- 业务路由：`代码/后端/后端代码/core/urls.py`
- AI HTTP 服务：`代码/AI服务/AI服务器代码/ai_http_service.py`
- AI 服务核心：`代码/AI服务/AI服务器代码/detection_service/service.py`
- AI 契约结构：`代码/AI服务/AI服务器代码/detection_service/contracts.py`

## 2. 接口分层

### 2.1 后端业务接口
统一前缀：

```text
/api/
```

WebSocket 实时通知：

```text
/ws/notifications/
```

### 2.2 AI 服务内部接口
默认本地开发地址：

```text
http://127.0.0.1:8010
```

主要接口：

- `GET /health`
- `POST /api/v1/image-detection/batches`
- `GET /api/v1/admin/model-registry`

## 3. 通用约定
- 需要登录的后端接口依赖当前用户上下文进行权限校验。
- 文件上传接口通常使用 `multipart/form-data`。
- 文件下载接口返回文件流，其余接口以 JSON 为主。
- AI 服务当前只提供 `image` 任务的真实检测链路。
- AI 服务已预留 `paper` 和 `review` 任务类型，但目前仅作占位，不提供真实检测结果。

## 4. 用户认证与个人信息接口

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/register/` | `POST` | 用户注册 |
| `/api/login/` | `POST` | 普通用户登录 |
| `/api/logout/` | `POST` | 用户登出 |
| `/api/token/refresh/` | `POST` | 刷新令牌 |
| `/api/user/details/` | `GET` | 获取当前用户详情 |
| `/api/user/update/` | `PUT` | 更新当前用户资料 |
| `/api/user/avatar/` | `PUT` | 更新头像 |
| `/api/password-reset/` | `POST` | 请求密码重置验证码 |
| `/api/password-reset/confirm/` | `POST` | 提交验证码并重置密码 |
| `/api/admin-login/` | `POST` | 管理员登录 |

## 5. 用户任务、配额与个人记录接口

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/detection-task/<task_id>/status/` | `GET` | 用户端查询检测任务状态 |
| `/api/task-summary/` | `GET` | 当前用户任务摘要 |
| `/api/get-task-summary/` | `GET` | 任务汇总信息 |
| `/api/user-tasks/` | `GET` | 当前用户检测任务列表 |
| `/api/organization/usage/` | `GET` | 查询组织使用情况 |
| `/api/organization/recharge-uses/` | `POST` | 补充检测次数 |
| `/api/single-user-action-log/` | `GET` | 当前用户个人操作日志 |
| `/api/reviewer/tasks/` | `GET` | 审核人员任务列表 |
| `/api/reviewer/activity_logs/` | `GET` | 审核人员活动日志 |
| `/api/manual-review/<review_id>/report/` | `GET` | 生成或下载人工审核报告 |

## 6. 文件上传与资源管理接口

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/upload/` | `POST` | 上传图片、PDF、压缩包等资源 |
| `/api/upload/<file_id>/` | `GET` | 获取上传文件详情 |
| `/api/upload/<file_id>/extract_images/` | `GET` | 获取文件中提取的图片 |
| `/api/upload/<file_id>/addTag/` | `POST` | 更新文件标签 |
| `/api/upload/<file_id>/delete/` | `DELETE` | 删除上传文件 |
| `/api/upload/get_all_file_images/<file_management_id>/` | `GET` | 获取某文件对应的全部图片 |

## 7. 图像检测、结果与报告接口

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/detection/submit/` | `POST` | 提交图像检测任务 |
| `/api/detection/<image_id>/` | `GET` | 获取单张图片检测结果 |
| `/api/tasks/<task_id>/results/` | `GET` | 获取任务全部检测结果 |
| `/api/tasks/<task_id>/fake_results/` | `GET` | 获取任务中判定异常的结果 |
| `/api/tasks/<task_id>/normal_results/` | `GET` | 获取任务中判定正常的结果 |
| `/api/results/<result_id>/` | `GET` | 获取单条检测结果详情 |
| `/api/results_image/<image_id>/` | `GET` | 按图片获取检测结果 |
| `/api/tasks_image/<image_id>/getdr/` | `GET` | 按图片获取检测结果映射 |
| `/api/tasks/<task_id>/report/` | `GET` | 下载任务级检测报告 |
| `/api/tasks_image/<image_id>/report/` | `GET` | 下载图片级检测报告 |
| `/api/detection-task-delete/<task_id>/` | `DELETE` | 删除检测任务 |

## 8. 人工审核接口

### 8.1 审核申请与审核任务

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/publishers/<publisher_id>/reviewers/` | `GET` | 获取某发布者可选审核人 |
| `/api/create_review_task_with_admin_check/` | `POST` | 创建人工审核申请并进入管理员审批流程 |
| `/api/get_request_completion_status/<task_id>/` | `GET` | 查询审核申请完成状态 |
| `/api/get_request_detail/<reviewRequest_id>/` | `GET` | 获取审核申请详情 |
| `/api/get_reviewer_tasks/` | `GET` | 获取审核人员待处理任务 |
| `/api/get_all_reviewers/` | `GET` | 获取组织内审核人员列表 |
| `/api/get_publisher_review_tasks/` | `GET` | 获取发布者发起的审核任务列表 |
| `/api/get-reviewer-request-detail/<reviewRequest_id>/` | `GET` | 审核人员查看审核申请详情 |

### 8.2 审核结果查询与提交

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/get_img_review_all/` | `GET` | 获取某审核任务的全部图片审核结果 |
| `/api/get_image_review/` | `GET` | 获取指定图片审核结果 |
| `/api/get_review_detail/<manual_review_id>/` | `GET` | 获取单个人工审核详情 |
| `/api/post_review/<manual_review_id>/` | `POST` | 提交人工审核结果 |
| `/api/manual-review/<review_request_id>/` | `GET` | 通过审核申请获取关联人工审核记录 |
| `/api/publisher-dectectiontask-access/` | `GET` | 检查发布者是否可访问某检测任务 |
| `/api/reviewer-manualreview-access/` | `GET` | 检查审核人员是否可访问某人工审核记录 |

## 9. 通知与消息接口

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/notification/get/` | `GET` | 获取通知列表 |
| `/api/notification/notify/` | `GET` | 获取未读通知数量 |
| `/api/notification/set_as_read/` | `POST` | 全部标记为已读 |
| `/api/notification/set_as_read/<notification_id>/` | `POST` | 单条标记为已读 |
| `/api/notification/broadcast/` | `POST` | 管理员广播通知 |
| `/ws/notifications/` | `WebSocket` | 实时通知推送通道 |

## 10. 组织管理接口

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/organizations/create-directly/` | `POST` | 管理端直接创建组织 |
| `/api/organization/create/` | `POST` | 提交组织申请 |
| `/api/organization/applications/get_pending/` | `GET` | 获取待审批组织申请列表 |
| `/api/organization/applications/<app_id>/` | `GET` | 获取组织申请详情 |
| `/api/organization/<app_id>/approve/` | `POST` | 通过组织申请 |
| `/api/organization/<app_id>/reject/` | `POST` | 拒绝组织申请 |
| `/api/organization/<org_id>/invitation_codes/` | `GET` | 获取组织邀请码列表 |
| `/api/organizations/` | `GET` | 获取组织列表 |
| `/api/organization/<org_id>/` | `GET` | 获取组织详情 |
| `/api/organization/<org_id>/delete/` | `DELETE` | 删除组织 |
| `/api/organization/<org_id>/permission/` | `POST` | 更新组织角色权限 |

## 11. 管理端接口

### 11.1 管理员与用户管理

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/admin/details/` | `GET` | 获取当前管理员详情 |
| `/api/admin/details/<user_id>` | `GET` | 获取指定用户详情 |
| `/api/get_users/` | `GET` | 获取用户列表 |
| `/api/create_user/` | `POST` | 创建用户 |
| `/api/update_user/<user_id>/` | `PUT` | 更新用户 |
| `/api/delete_user/<user_id>/` | `DELETE` | 删除用户 |
| `/api/create-admin/` | `POST` | 创建管理员 |
| `/api/user_permission/<user_id>/` | `POST` | 更新用户权限 |
| `/api/manage-associations/` | `POST` | 建立发布者与审核者关联关系 |

### 11.2 文件与审核治理

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/get_files/` | `GET` | 获取文件列表 |
| `/api/get_reviewRequest/all/` | `GET` | 获取全部审核申请 |
| `/api/get_reviewRequest/<reviewRequest_id>/` | `GET` | 获取审核申请详情 |
| `/api/get_review_request_detail/<manual_review_id>/` | `GET` | 获取人工审核详情 |
| `/api/handle_reviewRequest/<reviewRequest_id>/` | `POST` | 管理员处理审核申请 |
| `/api/delete_image_upload/<image_id>/` | `DELETE` | 删除图片上传记录 |
| `/api/post_report/<post_id>/` | `POST` | 处理举报 |

### 11.3 日志接口

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/user_action_log/` | `GET` | 获取用户操作日志 |
| `/api/user_action_log/<log_id>/` | `DELETE` | 删除日志 |
| `/api/user_action_log/download/` | `GET` | 导出日志 |

### 11.4 仪表盘与统计接口

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/admin_dashboard/` | `GET` | 仪表盘汇总信息 |
| `/api/dashboard/img_tag/` | `GET` | 图像标签统计 |
| `/api/dashboard/top_publishers/` | `GET` | 发布者排行 |
| `/api/dashboard/top_organizations/` | `GET` | 组织排行 |
| `/api/dashboard/daily_active_users/` | `GET` | 日活用户统计 |
| `/api/dashboard/daily_active_organizations/` | `GET` | 日活组织统计 |
| `/api/dashboard/daily_task_count/` | `GET` | 每日检测任务数量 |
| `/api/dashboard/daily_review_request_count/` | `GET` | 每日审核申请数量 |
| `/api/dashboard/daily_completed_manual_review_count/` | `GET` | 每日完成人工审核数量 |
| `/api/dashboard/get_sub_method_distribution_by_tag/` | `GET` | 子检测方法分布统计 |
| `/api/get_task_summary/` | `GET` | 管理端任务汇总 |
| `/api/get_detection_task_status/<task_id>/` | `GET` | 管理端检测任务状态 |
| `/api/get_all_user_tasks/` | `GET` | 管理端查询所有用户任务 |

## 12. AI 服务内部接口

### 12.1 健康检查

| 路径 | 方法 | 说明 |
|---|---|---|
| `/health` | `GET` | 返回 AI 服务状态、支持任务、结果格式、profile 与热加载状态 |

当前健康检查响应包含的关键字段：

- `service`
- `service_version`
- `supported_tasks`
- `reserved_tasks`
- `result_format`
- `default_image_profile`
- `available_image_profiles`
- `reload_count`
- `last_reload_at`
- `last_reload_error`

### 12.2 图像批量检测

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/v1/image-detection/batches` | `POST` | AI 服务图像批量检测入口，供后端调用 |

请求关键字段：

- `task_type`：当前应为 `image`
- `batch_id`：批次标识，可选
- `model_version`：模型版本，可选
- `parameters.model_profile`：模型 profile，可选；课堂最小演示建议使用 `minimal_trainable`
- `items`：待检测图片列表

响应关键字段：

- `batch_id`
- `task_type`
- `model_version`
- `model_profile`
- `results`
- `results[].overall_is_fake`
- `results[].overall_confidence`
- `results[].sub_method_results`
- `results[].evidences`

说明：

- 返回中同时保留后端当前兼容字段与标准化证据对象。
- `evidences` 为标准化证据列表，是当前 AI 侧统一结果结构。

### 12.3 模型注册表查询

| 路径 | 方法 | 说明 |
|---|---|---|
| `/api/v1/admin/model-registry` | `GET` | 查询当前 AI 服务已加载的 registry、profile 和热加载状态 |

查询参数：

- `profile`：可选，传入后仅查看指定 profile 详情

用途：

- 验证服务当前启用了哪些检测方法
- 查看默认 profile 和默认模型版本
- 排查热加载后的当前生效配置

## 13. 当前后端与 AI 的协作关系
- 前端不直接调用 AI 服务。
- 前端调用 Django `/api/` 接口。
- Django 后端负责整理检测任务并调用 AI 服务 `/api/v1/image-detection/batches`。
- AI 服务返回兼容字段和标准化证据对象，后端当前继续消费兼容字段。
- AI 服务的配置热加载和模型注册查询当前仅暴露在 AI 侧，不直接透出给前端。

## 14. 已知接口层问题
- `core/urls.py` 中同时存在 `/api/task-summary/`、`/api/get-task-summary/`、`/api/get_task_summary/` 三类近似路径，命名风格不统一。
- `core/urls.py` 中存在一条定义为 `'/review-requests/<int:review_request_id>/delete/'` 的路由，前面额外带了斜杠，挂到 `/api/` 后可能形成异常路径。
- 后端业务接口当前仍然以图像检测为中心；论文检测和 Review 检测尚未形成与图像检测同等级的统一任务接口。
- AI 服务虽然已经预留 `paper` 和 `review`，但当前只有 `image` 任务具备可运行链路。

## 15. 后续演进建议
- 将后端资源对象继续从 `file_id`、`image_id` 扩展为统一资源标识。
- 将图像检测、论文检测、Review 检测收敛到统一任务提交与统一状态查询接口。
- 将 AI 服务的模型管理信息逐步纳入管理端统一治理视图。
- 收敛重复和风格不一致的路径命名，统一 REST 风格。
