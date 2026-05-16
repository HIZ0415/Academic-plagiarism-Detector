# utils/report_generator.py
import os, textwrap, json
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..models import DetectionTask, DetectionResult, SubDetectionResult

# ─── 字体注册（宋体） ──────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
# 字体文件放在后端代码的根目录下，使用绝对路径避免工作目录问题
_FONT_DIR = Path(__file__).resolve().parent.parent.parent  # 指向 后端代码/ 目录
_SIMSUN_PATH = str(_FONT_DIR / 'SimSun.ttf')
_SIMSUN_BOLD_PATH = str(_FONT_DIR / 'SimSun-Bold.ttf')
try:
    pdfmetrics.registerFont(TTFont('SimSun', _SIMSUN_PATH))
    pdfmetrics.registerFont(TTFont('SimSun-Bold', _SIMSUN_BOLD_PATH))
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"字体注册失败，PDF报告将使用默认字体: {e}")


def _font(bold=False):
    """有 SimSun 则用宋体，否则回退 Helvetica（避免字体缺失导致 500）。"""
    try:
        name = 'SimSun-Bold' if bold else 'SimSun'
        pdfmetrics.getFont(name)
        return name
    except Exception:
        return 'Helvetica-Bold' if bold else 'Helvetica'


# ─── 工具函数：自动换行绘制 ───────────────────────────────
def _draw_multiline(c, x, y, text, max_chars=48, leading=14, font=None, size=9):
    font = font or _font()
    c.setFont(font, size)
    for line in textwrap.wrap(text, width=max_chars):
        c.drawString(x, y, line)
        y -= leading
    return y


MAX_CONTENT_HEIGHT = 40


def _check_and_create_new_page(c, y, H, MARGIN):
    """检查剩余空间，若不足则创建新页面"""
    if y - MAX_CONTENT_HEIGHT < MARGIN:
        c.showPage()  # 新页面
        y = H - MARGIN  # 重置 y 坐标
    return y


def generate_detection_task_report(task: DetectionTask) -> str:
    """
    生成 PDF 报告（中文），返回相对路径，并写入 task.report_file
    """
    # 生成路径
    rel_path = f"reports/task_{task.id}_report.pdf"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # 画布
    c = canvas.Canvas(abs_path, pagesize=A4)
    W, H = A4
    MARGIN = 40

    # ────────────────────────── 封面页 ──────────────────────────
    c.bookmarkPage("cover")
    c.addOutlineEntry("任务概览", "cover", level=0)

    y = H - 120
    c.setFont("SimSun-Bold", 40)
    c.drawCentredString(W / 2, y, '“听泉鉴图”图像造假检测报告')
    y -= 80

    c.setFont("SimSun", 24)
    c.drawString(MARGIN, y, f"任务编号：{task.id}")
    y -= 40
    c.drawString(MARGIN, y, f"任务名称：{task.task_name}")
    y -= 40
    c.drawString(MARGIN, y, f"用户：{task.user.username}")
    y -= 40

    create_time = timezone.localtime(task.upload_time).strftime("%Y-%m-%d %H:%M")
    finish_time = task.completion_time and timezone.localtime(task.completion_time).strftime("%Y-%m-%d %H:%M")
    c.drawString(MARGIN, y, f"创建时间：{create_time}")
    y -= 40
    if finish_time:
        c.drawString(MARGIN, y, f"完成时间：{finish_time}")
        y -= 40

    # 参数
    y -= 10
    c.setFont("SimSun-Bold", 24)
    c.drawString(MARGIN, y, "检测参数")
    y -= 36
    c.setFont("SimSun", 22)
    c.drawString(MARGIN, y, f"cmd_block_size：{task.cmd_block_size}")
    y -= 36
    c.drawString(MARGIN, y, f"urn_k：{task.urn_k}")
    y -= 36
    c.drawString(MARGIN, y, f"使用大语言模型：{'是' if task.if_use_llm else '否'}")

    c.showPage()

    # ─────────────────────── 每张图片一页 ──────────────────────
    for idx, dr in enumerate(
            task.detection_results.select_related("image_upload").prefetch_related("sub_results").order_by("id"),
            start=1
    ):
        page_label = f"图片 {dr.image_upload.id}"
        c.bookmarkPage(f"img_{dr.image_upload.id}")
        c.addOutlineEntry(page_label, f"img_{dr.image_upload.id}", level=1)

        y = H - MARGIN
        c.setFont("SimSun-Bold", 14)
        c.drawString(MARGIN, y, page_label)
        y -= 25

        # 原图
        orig_path = dr.image_upload.image.path
        # if os.path.exists(orig_path):
        #     c.drawImage(ImageReader(orig_path), MARGIN, y-280, width=220, height=220, preserveAspectRatio=True)
        # orig_path = dr.image_upload.image.path
        if os.path.exists(orig_path):
            # 调整原图的位置，确保与其他部分内容不重叠
            c.drawImage(ImageReader(orig_path), MARGIN, y - 100, width=100, height=100, preserveAspectRatio=True)
            # 更新 y 坐标，确保图像与后续内容的间距
            y -= 100  # 图片高度 + 适当的间距
        # 总体结论
        c.setFont("SimSun", 11)
        c.drawString(MARGIN, y - 20, f"判定：{'造假' if dr.is_fake else '真实'}")
        c.drawString(MARGIN, y - 45, f"造假概率：{dr.confidence_score:.2f}")
        y -= 70

        # LLM 结果
        if task.if_use_llm:
            y -= 10
            c.setFont("SimSun-Bold", 11)
            c.drawString(MARGIN, y, "大语言模型分析：")
            y -= 18
            y = _draw_multiline(c, MARGIN + 15, y, dr.llm_judgment or "无", max_chars=50)
            y -= 110
            if dr.llm_image and os.path.exists(dr.llm_image.path):
                c.drawImage(ImageReader(dr.llm_image.path), MARGIN + 90, y, width=100, height=100,
                            preserveAspectRatio=True)
            y -= 10

        # ELA 与 EXIF
        if dr.ela_image and os.path.exists(dr.ela_image.path):
            c.drawString(MARGIN, y, "ELA 可视化：")
            c.drawImage(ImageReader(dr.ela_image.path), MARGIN + 90, y - 100, width=100, height=100,
                        preserveAspectRatio=True)
            y -= 10
        exif_txt = f"EXIF：Photoshop 痕迹 [{'有' if dr.exif_photoshop else '无'}]   时间修改 [{'有' if dr.exif_time_modified else '无'}]"
        c.drawString(MARGIN, y - 110, exif_txt)
        y -= 130

        # 子方法
        c.setFont("SimSun-Bold", 11)
        c.drawString(MARGIN, y, "深度学习检测方法：")
        y -= 20
        for sub in dr.sub_results.all():
            y = _check_and_create_new_page(c, y, H, MARGIN)  # 调用检查函数
            c.setFont("SimSun", 10)
            c.drawString(MARGIN + 10, y, f"{sub.method}  造假概率：{sub.probability:.2f}")
            if sub.mask_image and os.path.exists(sub.mask_image.path):
                c.drawImage(ImageReader(sub.mask_image.path), MARGIN + 220, y - 40, width=60, height=60,
                            preserveAspectRatio=True)
            y -= 70

        c.showPage()

    # ─────────────────────────── 保存 ──────────────────────────
    c.save()
    task.report_file = rel_path
    task.save(update_fields=["report_file"])
    return rel_path


from ..models import ManualReview, ImageReview


def _manual_review_result_label(result):
    if result is True:
        return "判定存在疑似造假"
    if result is False:
        return "未发现明显异常"
    return "未判定"


def _iter_manual_image_reviews(review: ManualReview):
    seen = set()
    for ir in review.img_reviews.all():
        if ir.id not in seen:
            seen.add(ir.id)
            yield ir
    for ir in review.image_reviews.all():
        if ir.id not in seen:
            seen.add(ir.id)
            yield ir


def generate_manual_review_report(review: ManualReview) -> str:
    """
    生成人工审核 PDF 报告，返回相对路径，并写入 review.report_file
    """
    rel_path = f"reports/manual_review_{review.id}_report.pdf"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    rr = review.review_request
    detection_task = None
    task_type = ""
    if rr and rr.detection_result:
        detection_task = rr.detection_result.detection_task
        task_type = (detection_task.task_type or "") if detection_task else ""

    c = canvas.Canvas(abs_path, pagesize=A4)
    W, H = A4
    MARGIN = 40
    fn, fb = _font(), _font(bold=True)

    c.bookmarkPage("cover")
    c.addOutlineEntry("人工审核概览", "cover", level=0)

    y = H - MARGIN - 20
    c.setFont(fb, 22)
    c.drawCentredString(W / 2, y, "学术内容诚信检测 — 人工审核报告")
    y -= 50

    c.setFont(fn, 12)
    c.drawString(MARGIN, y, f"人工审核记录 ID：{review.id}")
    y -= 22
    if rr:
        c.drawString(MARGIN, y, f"申请单号：{rr.id}")
        y -= 22
    if detection_task:
        c.drawString(MARGIN, y, f"检测任务 ID：{detection_task.id}（{task_type or '—'}）")
        y -= 22
        if detection_task.task_name:
            c.drawString(MARGIN, y, f"任务名称：{detection_task.task_name}")
            y -= 22

    publisher_name = rr.user.username if rr and rr.user_id else "—"
    c.drawString(MARGIN, y, f"发布者：{publisher_name}")
    y -= 22
    c.drawString(MARGIN, y, f"专家：{review.reviewer.username if review.reviewer_id else '未指定'}")
    y -= 22

    start_time = timezone.localtime(review.review_time).strftime("%Y-%m-%d %H:%M")
    end_time = rr.review_end_time if rr else None
    finish_time = (
        timezone.localtime(end_time).strftime("%Y-%m-%d %H:%M") if end_time else "尚未完成"
    )
    c.drawString(MARGIN, y, f"审核时间：{start_time} — {finish_time}")
    y -= 30

    if rr and (rr.reason or "").strip():
        c.setFont(fb, 13)
        c.drawString(MARGIN, y, "发布者申请说明：")
        y -= 18
        c.setFont(fn, 11)
        y = _draw_multiline(c, MARGIN, y, (rr.reason or "")[:800], max_chars=70, font=fn, size=11)
        y -= 20

    image_reviews = list(_iter_manual_image_reviews(review))
    is_textual = "paper" in task_type.lower() or "review" in task_type.lower()

    c.setFont(fb, 14)
    section_title = "材料单元审核明细" if is_textual else "图像审核明细"
    c.drawString(MARGIN, y, section_title)
    y -= 22

    if not image_reviews:
        c.setFont(fn, 11)
        y = _draw_multiline(c, MARGIN, y, "暂无结构化审核条目。", max_chars=70, font=fn, size=11)
        y -= 20
    else:
        for idx, img_review in enumerate(image_reviews, start=1):
            if y < MARGIN + 120:
                c.showPage()
                y = H - MARGIN

            label = f"单元 {idx}" if is_textual else f"图片 {getattr(img_review.img, 'id', idx)}"
            c.setFont(fb, 12)
            c.drawString(MARGIN, y, label)
            y -= 18

            image_upload = img_review.img
            if image_upload and not is_textual:
                try:
                    image_path = image_upload.image.path if image_upload.image else None
                    if image_path and os.path.exists(image_path):
                        c.drawImage(
                            ImageReader(image_path),
                            MARGIN,
                            y - 100,
                            width=100,
                            height=100,
                            preserveAspectRatio=True,
                        )
                        y -= 110
                except Exception:
                    pass

            c.setFont(fn, 11)
            c.drawString(MARGIN, y, f"最终判定：{_manual_review_result_label(img_review.result)}")
            y -= 18
            rt = img_review.review_time
            if rt:
                c.drawString(
                    MARGIN,
                    y,
                    f"记录时间：{timezone.localtime(rt).strftime('%Y-%m-%d %H:%M')}",
                )
                y -= 18

            c.setFont(fb, 11)
            c.drawString(MARGIN, y, "各维度评分与理由：")
            y -= 16
            c.setFont(fn, 10)
            for i in range(1, 8):
                score = getattr(img_review, f"score{i}", None)
                reason = getattr(img_review, f"reason{i}", None)
                if score is None and not reason:
                    continue
                line = f"维度 {i}：得分 {score if score is not None else '—'}；理由：{reason or '无'}"
                y = _draw_multiline(c, MARGIN + 8, y, line, max_chars=78, font=fn, size=10)
                y -= 6
                if y < MARGIN + 60:
                    c.showPage()
                    y = H - MARGIN
            y -= 12

    c.save()
    review.report_file = rel_path
    review.save(update_fields=["report_file"])
    return rel_path

# ═══════════════════════════════════════════════════════════════════════════════
#  任务 019 – 统一报告生成（论文 / Review）
# ═══════════════════════════════════════════════════════════════════════════════

def _load_result_json(task, result_type=None):
    """读取 Celery 落盘的检测结果 JSON。"""
    media = Path(settings.MEDIA_ROOT)
    if task.task_type in ('paper_aigc', 'resource_check'):
        fname = f"{task.paper_file_id}_{result_type or task.task_type.split('_', 1)[-1]}_result.json"
        if task.task_type == 'paper_aigc':
            fname = f"{task.paper_file_id}_aigc_result.json"
        else:
            fname = f"{task.paper_file_id}_resource_result.json"
        p = media / "paper_uploads" / fname
    elif task.task_type == 'review_detection':
        p = media / "review_uploads" / f"{task.paper_file_id}_detection_result.json"
    else:
        return None
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _risk_label(level):
    return {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(level, level or "未知")


def generate_paper_aigc_report(task: DetectionTask) -> str:
    """生成论文 AIGC 检测 PDF 报告。"""
    result = _load_result_json(task)
    rel_path = f"reports/task_{task.id}_paper_aigc_report.pdf"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    c = canvas.Canvas(abs_path, pagesize=A4)
    W, H = A4
    MARGIN = 40

    # 封面
    y = H - 100
    c.setFont(_font(bold=True), 28)
    c.drawCentredString(W / 2, y, 'AIGC Detection Report')
    y -= 60

    c.setFont(_font(), 14)
    info = [
        f"Task ID: {task.id}",
        f"Task Name: {task.task_name}",
        f"User: {task.user.username}",
        f"Created: {timezone.localtime(task.upload_time).strftime('%Y-%m-%d %H:%M')}",
    ]
    if task.completion_time:
        info.append(f"Completed: {timezone.localtime(task.completion_time).strftime('%Y-%m-%d %H:%M')}")
    for line in info:
        c.drawString(MARGIN, y, line)
        y -= 24

    if result:
        y -= 20
        c.setFont(_font(bold=True), 16)
        c.drawString(MARGIN, y, 'Overall')
        y -= 28
        c.setFont(_font(), 12)
        ratio = result.get("ai_contribution_ratio", 0)
        c.drawString(MARGIN, y, f"AI Contribution: {round(ratio * 100, 1)}%")
        y -= 20
        c.drawString(MARGIN, y, f"Risk Level: {_risk_label(result.get('overall_risk_level'))}")
        y -= 20
        summary = result.get("summary", "")
        if summary:
            y = _draw_multiline(c, MARGIN, y, summary, max_chars=70, font=_font(), size=11)
        y -= 30

        # 段落详情
        paragraphs = result.get("paragraphs", [])
        if paragraphs:
            c.setFont(_font(bold=True), 14)
            c.drawString(MARGIN, y, f'Paragraph Analysis ({len(paragraphs)} paragraphs)')
            y -= 24
            for p in paragraphs:
                y = _check_and_create_new_page(c, y, H, MARGIN)
                c.setFont(_font(), 10)
                c.drawString(MARGIN + 10, y,
                             f"P{p.get('index', '?')}: score={p.get('risk_score', 0):.3f} "
                             f"[{_risk_label(p.get('risk_level'))}]")
                y -= 16
                excerpt = p.get("excerpt", "")[:120]
                if excerpt:
                    y = _draw_multiline(c, MARGIN + 20, y, excerpt, max_chars=65, font=_font(), size=9)
                    y -= 8
    else:
        y -= 20
        c.setFont(_font(), 12)
        c.drawString(MARGIN, y, "No result data available.")

    c.showPage()
    c.save()
    task.report_file = rel_path
    task.save(update_fields=["report_file"])
    return rel_path


def generate_resource_check_report(task: DetectionTask) -> str:
    """生成学术资源检测 PDF 报告。"""
    result = _load_result_json(task)
    rel_path = f"reports/task_{task.id}_resource_check_report.pdf"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    c = canvas.Canvas(abs_path, pagesize=A4)
    W, H = A4
    MARGIN = 40

    y = H - 100
    c.setFont(_font(bold=True), 28)
    c.drawCentredString(W / 2, y, 'Resource Check Report')
    y -= 60

    c.setFont(_font(), 14)
    for line in [f"Task ID: {task.id}", f"Task Name: {task.task_name}",
                 f"User: {task.user.username}"]:
        c.drawString(MARGIN, y, line)
        y -= 24

    if result:
        y -= 20
        c.setFont(_font(bold=True), 16)
        c.drawString(MARGIN, y, 'Summary')
        y -= 28
        c.setFont(_font(), 12)
        c.drawString(MARGIN, y, f"References found: {result.get('total_references', 0)}")
        y -= 20
        c.drawString(MARGIN, y, f"DOI found: {result.get('doi_found_count', 0)}")
        y -= 20
        c.drawString(MARGIN, y, f"Suspected risks: {result.get('suspected_risk_count', 0)}")
        y -= 30

        issues = result.get("issues", [])
        if issues:
            c.setFont(_font(bold=True), 14)
            c.drawString(MARGIN, y, f'Issues ({len(issues)})')
            y -= 24
            for iss in issues:
                y = _check_and_create_new_page(c, y, H, MARGIN)
                c.setFont(_font(), 10)
                c.drawString(MARGIN + 10, y,
                             f"Ref#{iss.get('reference_index')}: "
                             f"{iss.get('issue_type', '')} [{iss.get('severity', '')}]")
                y -= 16
                detail = iss.get("detail", "")
                if detail:
                    y = _draw_multiline(c, MARGIN + 20, y, detail, max_chars=65, font=_font(), size=9)
                    y -= 8

    c.showPage()
    c.save()
    task.report_file = rel_path
    task.save(update_fields=["report_file"])
    return rel_path


def generate_review_detection_report(task: DetectionTask) -> str:
    """生成 Review 检测 PDF 报告。"""
    result = _load_result_json(task)
    rel_path = f"reports/task_{task.id}_review_detection_report.pdf"
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    c = canvas.Canvas(abs_path, pagesize=A4)
    W, H = A4
    MARGIN = 40

    y = H - 100
    c.setFont(_font(bold=True), 28)
    c.drawCentredString(W / 2, y, 'Review Detection Report')
    y -= 60

    c.setFont(_font(), 14)
    for line in [f"Task ID: {task.id}", f"Task Name: {task.task_name}",
                 f"User: {task.user.username}"]:
        c.drawString(MARGIN, y, line)
        y -= 24

    if result:
        y -= 20
        c.setFont(_font(bold=True), 16)
        c.drawString(MARGIN, y, 'Overall')
        y -= 28
        c.setFont(_font(), 12)
        ai_prob = result.get("overall_ai_probability", 0)
        c.drawString(MARGIN, y, f"AI Probability: {round(ai_prob * 100, 1)}%")
        y -= 20
        c.drawString(MARGIN, y, f"Risk Level: {_risk_label(result.get('overall_risk_level'))}")
        y -= 20
        tpl = result.get("template_score", 0)
        c.drawString(MARGIN, y, f"Template Score: {round(tpl * 100, 1)}%  "
                                f"({'Template-like' if result.get('is_template_like') else 'Original'})")
        y -= 20
        summary = result.get("summary", "")
        if summary:
            y = _draw_multiline(c, MARGIN, y, summary, max_chars=70, font=_font(), size=11)
        y -= 30

        sentences = result.get("sentences", [])
        if sentences:
            c.setFont(_font(bold=True), 14)
            c.drawString(MARGIN, y, f'Sentence Analysis ({len(sentences)} sentences)')
            y -= 24
            for s in sentences:
                y = _check_and_create_new_page(c, y, H, MARGIN)
                c.setFont(_font(), 10)
                c.drawString(MARGIN + 10, y,
                             f"S{s.get('index', '?')}: prob={s.get('ai_probability', 0):.3f} "
                             f"[{_risk_label(s.get('risk_level'))}]")
                y -= 16
                text = s.get("text", "")[:120]
                if text:
                    y = _draw_multiline(c, MARGIN + 20, y, text, max_chars=65, font=_font(), size=9)
                    y -= 8

    c.showPage()
    c.save()
    task.report_file = rel_path
    task.save(update_fields=["report_file"])
    return rel_path


def generate_unified_task_report(task: DetectionTask) -> str:
    """根据 task_type 分发到对应的报告生成器。"""
    dispatch = {
        'image_detection': generate_detection_task_report,
        'paper_aigc': generate_paper_aigc_report,
        'resource_check': generate_resource_check_report,
        'review_detection': generate_review_detection_report,
    }
    generator = dispatch.get(task.task_type)
    if generator is None:
        raise ValueError(f"Unknown task_type: {task.task_type}")
    return generator(task)


# # utils/report_generator.py
# import os, textwrap, json
# from datetime import datetime
# from django.conf import settings
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4
# from reportlab.lib.utils import ImageReader
# from ..models import DetectionTask, DetectionResult, SubDetectionResult
# from django.utils import timezone
# from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
#
# pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.ttf'))  # 中文字体
# pdfmetrics.registerFont(TTFont('SimSun-Bold', 'SimSun-Bold.ttf'))  # 中文加粗字体
#
#
# def _draw_multiline(c, x, y, text, max_chars=90, leading=12):
#     """把长文本自动换行绘到 PDF"""
#     for line in textwrap.wrap(text, width=max_chars):
#         c.drawString(x, y, line)
#         y -= leading
#     return y
#
#
# def generate_detection_task_report(task: DetectionTask) -> str:
#     """
#     生成任务 PDF，返回相对路径（保存到 task.report_file）
#     """
#     # 保存到 MEDIA_ROOT/reports/task_<id>_report.pdf
#     rel_path = f"reports/task_{task.id}_report.pdf"
#     abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
#     os.makedirs(os.path.dirname(abs_path), exist_ok=True)
#
#     c = canvas.Canvas(abs_path, pagesize=A4)
#     W, H = A4
#     MARGIN = 40
#     y = H - MARGIN
#
#     # ─── 任务标题 ─────────────────────────────────────────────
#     c.setFont("Helvetica-Bold", 18)
#     c.drawString(MARGIN, y, f"Detection Report  (Task #{task.id})")
#     c.setFont("Helvetica", 10)
#     y -= 20
#     c.drawString(MARGIN, y, f"User: {task.user.username}    Created: {timezone.localtime(task.upload_time):%Y-%m-%d %H:%M}")
#     y -= 25
#
#     # ─── 遍历每张图 ──────────────────────────────────────────
#     for dr in task.detection_results.select_related("image_upload").prefetch_related("sub_results"):
#         if y < 250:                # 简单分页
#             c.showPage()
#             y = H - MARGIN
#
#         # 1) 总结行
#         c.setFont("Helvetica-Bold", 12)
#         c.drawString(MARGIN, y, f"Image #{dr.image_upload.id}")
#         y -= 15
#         c.setFont("Helvetica", 10)
#         c.drawString(MARGIN, y, f"Overall fake: {dr.is_fake}      Confidence: {dr.confidence_score:.2f}")
#         y -= 15
#
#         # 2) LLM 判断S
#         if dr.llm_judgment:
#             c.setFont("SimSun", 9)
#             y = _draw_multiline(c, MARGIN, y, f"大模型检测结果：{dr.llm_judgment}", max_chars=50, leading=12)
#             # y = _draw_multiline(c, MARGIN, y, f"LLM judgment: {dr.llm_judgment}")
#
#         # 3) EXIF & ELA
#         c.setFont("Helvetica", 10)
#         exif_str = f"EXIF  PhotoshopEdited: {dr.exif_photoshop} | TimeModified: {dr.exif_time_modified}"
#         c.drawString(MARGIN, y, exif_str)
#         y -= 15
#         if dr.ela_image:
#             ela_path = os.path.join(settings.MEDIA_ROOT, dr.ela_image.name)
#             if os.path.exists(ela_path):
#                 c.drawImage(ImageReader(ela_path), MARGIN, y-120, width=120, height=120, preserveAspectRatio=True)
#                 c.drawString(MARGIN, y-130, "ELA mask")
#         y -= 140
#
#         # 4) 子检测方法
#         c.setFont("Helvetica-Bold", 10)
#         c.drawString(MARGIN, y, "Sub-method results:")
#         y -= 15
#         for sub in dr.sub_results.all():
#             c.setFont("Helvetica", 9)
#             c.drawString(MARGIN+5, y, f"{sub.method}:  {sub.probability:.2f}")
#             if sub.mask_image:
#                 mask_path = os.path.join(settings.MEDIA_ROOT, sub.mask_image.name)
#                 if os.path.exists(mask_path):
#                     c.drawImage(ImageReader(mask_path), MARGIN+150, y-50, width=80, height=80, preserveAspectRatio=True)
#             y -= 100
#
#         y -= 10  # 间距
#
#     c.save()
#     task.report_file = rel_path
#     task.save(update_fields=["report_file"])
#     return rel_path
