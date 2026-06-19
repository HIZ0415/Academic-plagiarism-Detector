# 后端 API 文档

本文档为后端接口正式交付摘要。完整接口总览见：

```text
文档/APIs/current-project-api.md
```

## 1. 接口前缀

Django 业务接口统一挂载在：

```text
/api/
```

除注册、登录、密码重置等公开接口外，业务接口默认使用 JWT：

```http
Authorization: Bearer <access_token>
```

## 2. 用户与认证

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/register/` | 用户注册 |
| POST | `/api/login/` | 用户端登录 |
| POST | `/api/admin-login/` | 管理端登录 |
| POST | `/api/logout/` | 登出 |
| POST | `/api/token/refresh/` | 刷新令牌 |
| GET | `/api/user/details/` | 当前用户详情 |
| PUT | `/api/user/update/` | 更新用户资料 |
| PUT | `/api/user/avatar/` | 更新头像 |
| POST | `/api/password-reset/` | 请求密码重置验证码 |
| POST | `/api/password-reset/confirm/` | 重置密码 |

## 3. 上传、图像检测与报告

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/upload/` | 上传图片、PDF、压缩包等资源 |
| GET | `/api/upload/<file_id>/` | 获取文件详情 |
| GET | `/api/upload/<file_id>/extract_images/` | 获取提取图片 |
| POST | `/api/detection/submit/` | 提交图像检测任务 |
| GET | `/api/detection-task/<task_id>/status/` | 查询检测任务状态 |
| GET | `/api/user-tasks/` | 当前用户任务列表 |
| GET | `/api/tasks/<task_id>/results/` | 获取任务结果 |
| GET | `/api/results/<result_id>/` | 获取单条结果详情 |
| GET | `/api/tasks/<task_id>/report/` | 下载任务报告 |
| GET | `/api/tasks/<task_id>/comprehensive-report/` | 综合鉴伪报告数据 |
| GET | `/api/tasks/<task_id>/comprehensive-report/download/` | 下载综合鉴伪报告 |

## 4. 论文与 Review 检测

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/paper/upload/` | 上传论文 PDF 并预处理 |
| POST | `/api/paper/aigc/submit/` | 提交论文 AIGC 检测 |
| GET | `/api/paper/tasks/<task_id>/status/` | 查询论文任务状态 |
| GET | `/api/paper/aigc/<task_id>/result/` | 查询论文 AIGC 结果 |
| POST | `/api/paper/resource-check/submit/` | 提交学术资源规范性检查 |
| GET | `/api/paper/resource-check/<task_id>/result/` | 查询资源检查结果 |
| POST | `/api/review/submit/` | 提交 Review 文本检测 |
| GET | `/api/review/tasks/<task_id>/status/` | 查询 Review 检测状态 |
| GET | `/api/review/tasks/<task_id>/result/` | 查询 Review 检测结果 |

约束：论文检测仅支持 `.pdf`；Review 检测支持在线文本和 `.txt` 文件。

## 5. 人工审核

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/manual-review-requests/` | 发布者创建人工审核申请 |
| GET | `/api/manual-review-requests/by-detection-task/` | 按检测任务查询审核申请 |
| GET | `/api/manual-review-requests/<review_request_id>/publisher-summary/` | 发布者查看审核汇总 |
| POST | `/api/manual-review-requests/<review_request_id>/cancel/` | 发布者取消申请 |
| GET | `/api/get_reviewer_tasks/` | 审稿人任务池 |
| GET | `/api/get_review_detail/<manual_review_id>/` | 审稿人查看任务详情 |
| POST | `/api/post_review/<manual_review_id>/` | 审稿人提交审核结果 |
| GET | `/api/get_reviewRequest/all/` | 管理端审核申请列表 |
| GET | `/api/get_reviewRequest/<reviewRequest_id>/` | 管理端审核申请详情 |
| POST | `/api/handle_reviewRequest/<reviewRequest_id>/` | 管理员审批申请 |
| GET | `/api/manual-review/<review_id>/report/` | 下载人工审核报告 |

## 6. 管理端

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin_dashboard/` | 管理端首页汇总 |
| GET | `/api/get_users/` | 用户列表 |
| POST | `/api/create_user/` | 创建用户 |
| PUT | `/api/update_user/<user_id>/` | 更新用户 |
| DELETE | `/api/delete_user/<user_id>/` | 删除用户 |
| GET | `/api/get_files/` | 文件列表 |
| GET | `/api/get_all_user_tasks/` | 所有用户任务 |
| GET | `/api/user_action_log/` | 操作日志 |
| GET | `/api/user_action_log/download/` | 导出日志 |
| GET | `/api/dashboard/img_tag/` | 标签统计 |
| GET | `/api/dashboard/top_publishers/` | 发布者排行 |
| GET | `/api/dashboard/top_organizations/` | 组织排行 |
| GET | `/api/dashboard/daily_task_count/` | 每日任务数 |

## 7. 组织、通知、反馈与模型配置

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/organization/create/` | 提交组织申请 |
| GET | `/api/organizations/` | 组织列表 |
| GET | `/api/organization/<org_id>/` | 组织详情 |
| GET | `/api/organization/<org_id>/invitation_codes/` | 邀请码 |
| GET | `/api/notification/get/` | 通知列表 |
| GET | `/api/notification/notify/` | 未读通知数量 |
| POST | `/api/notification/broadcast/` | 管理员广播 |
| POST | `/api/feedback/` | 点赞或评论 |
| POST | `/api/reports/submit/` | 用户举报 |
| GET | `/api/detection-models/` | 检测模型目录 |
| POST | `/api/detection-preferences/` | 更新检测偏好 |

## 8. AI 服务

AI 服务默认本地地址：

```text
http://127.0.0.1:8010
```

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/image-detection/batches` | 图像批量检测 |
| POST | `/api/v1/paper-detection/batches` | 论文检测扩展入口 |
| POST | `/api/v1/review-detection/batches` | Review 检测扩展入口 |
| GET | `/api/v1/admin/model-registry` | 模型注册表 |
