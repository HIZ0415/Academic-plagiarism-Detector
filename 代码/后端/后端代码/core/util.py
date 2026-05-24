from django.utils import timezone
from urllib.parse import urlencode
from .models import Notification, DetectionResult, ManualReview


def detection_task_type_label(task_type: str | None) -> str:
    labels = {
        "image_detection": "图像检测",
        "paper_aigc": "论文 AIGC 检测",
        "resource_check": "学术资源规范性检测",
        "review_detection": "Review 检测",
    }
    return labels.get(task_type or "", task_type or "检测")


def detection_history_url(task) -> str:
    query = {
        "detail_id": task.id,
        "task_type": task.task_type or "unknown",
        "status": task.status or "completed",
        "progress": "100",
        "source": "notification",
    }
    if getattr(task, "batch_session_id", None):
        query["batch_session_id"] = task.batch_session_id
    if getattr(task, "upload_time", None):
        query["upload_time"] = timezone.localtime(task.upload_time).strftime("%Y-%m-%d %H:%M:%S")
    if getattr(task, "completion_time", None):
        query["completion_time"] = timezone.localtime(task.completion_time).strftime("%Y-%m-%d %H:%M:%S")
    return f"/history?{urlencode(query)}"


def send_notification(receiver_id, receiver_name, sender_id=None, sender_name=None, category=None, title=None,
                      content=None, url=None):
    """
    发送通知
    :param receiver_id: 收件人ID
    :param receiver_name: 收件人名称
    :param sender_id: 发件人ID（可选）
    :param sender_name: 发件人名称（可选）
    :param category: 通知类型 (1:全局, 2:系统, 3:出版社给审稿人, 4:审稿人给出版社)
    :param title: 通知标题
    :param content: 通知内容
    """
    Notification.objects.create(
        receiver_id=str(receiver_id),
        receiver_name=receiver_name,
        sender_id=str(sender_id) if sender_id is not None else None,
        sender_name=sender_name,
        category=category,
        title=title,
        content=content,
        status='unread',
        notified_at=timezone.now(),
        url=url
    )


def notify_detection_task_completed(task):
    """检测任务完成后写入系统通知，供社区反馈「检测反馈」与顶栏通知中心展示。"""
    if not task or not getattr(task, "user_id", None):
        return
    label = detection_task_type_label(getattr(task, "task_type", None))
    task_name = (getattr(task, "task_name", None) or "检测任务").strip()
    send_notification(
        receiver_id=task.user_id,
        receiver_name=task.user.username,
        category=Notification.SYSTEM,
        title=f"{label}已完成",
        content=f"您的任务「{task_name}」（编号 {task.id}）已完成，点击查看检测结果。",
        url=detection_history_url(task),
    )


def send_ai_detection_complete_notification(user_id, user_name, task):
    """发送AI检测完成通知"""
    label = detection_task_type_label(getattr(task, "task_type", None))
    send_notification(
        receiver_id=user_id,
        receiver_name=user_name,
        category=Notification.SYSTEM,
        title=f"{label}已完成",
        content='AI检测已完成，请查看结果',
        url=detection_history_url(task) if hasattr(task, "task_type") else f"/history?detail_id={getattr(task, 'id', task)}",
    )
