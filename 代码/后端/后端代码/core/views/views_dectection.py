import json
import zipfile

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from ..models import DetectionResult, ImageUpload, Log, User
from django.db.models import Q
from datetime import datetime
from django.core.paginator import Paginator

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_detection_result(request, image_id):
    try:
        # 获取检测结果
        detection_result = DetectionResult.objects.get(image_upload_id=image_id,
                                                       image_upload__file_management__user=request.user)

        # 检查状态并返回相应数据
        if detection_result.status == 'in_progress':
            return Response({
                "image_id": detection_result.image_upload.id,
                "status": "正在检测中",
                "message": "AI检测正在进行，请稍等"
            })

        # 如果检测已完成
        return Response({
            "image_id": detection_result.image_upload.id,
            "status": "检测已完成",
            "is_fake": detection_result.is_fake,
            "confidence_score": detection_result.confidence_score,
            "detection_time": timezone.localtime(detection_result.detection_time)
        })

    except DetectionResult.DoesNotExist:
        return Response({"message": "Detection result not found"}, status=404)


from ..tasks import run_ai_detection, run_ai_detection_batch
from ..tasks_new import fetch_batch


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def submit_detection(request):
#     user_id = request.user.id
#     user = User.objects.get(id=user_id)
#     if not user.has_permission('submit'):
#         return Response({"错误": "该用户没有提交检测的权限"}, status=403)
#
#     # 获取用户提交的图像ID列表
#     image_ids = request.data.get('image_ids', [])
#     task_name = request.data.get('task_name', 'New Detection Task')  # 从请求中获取任务名称，默认为 "New Detection Task"
#
#     # 获取额外的参数
#     cmd_block_size = request.data.get('cmd_block_size', 64)  # 默认为64
#     urn_k = request.data.get('urn_k', 0.3)  # 默认为0.3
#     if_use_llm = request.data.get('if_use_llm', False)  # 默认为False
#
#     if not image_ids:
#         return Response({"message": "No image IDs provided"}, status=400)
#
#     # 查找用户上传的所有图像
#     image_uploads = ImageUpload.objects.filter(id__in=image_ids, file_management__user=request.user)
#
#     # 检验不为空
#     if not image_uploads.exists():
#         return Response({"message": "No valid images found"}, status=404)
#
#     # 创建一个新的检测任务
#     detection_task = DetectionTask.objects.create(
#         organization=user.organization,
#         user=request.user,
#         task_name=task_name,  # 使用用户提交的任务名称
#         status='pending',  # 初始状态为"排队中"
#         cmd_block_size=cmd_block_size,
#         urn_k=urn_k,
#         if_use_llm=if_use_llm
#     )
#
#     # 在Log表中记录检测任务的创建
#     Log.objects.create(
#         user=request.user,
#         operation_type='detection',
#         related_model='DetectionTask',
#         related_id=detection_task.id
#     )
#
#     # 对每个图像生成检测记录，并将状态设置为"正在检测中"
#     for image_upload in image_uploads:
#         detection_result, created = DetectionResult.objects.get_or_create(
#             image_upload=image_upload,
#             detection_task=detection_task,  # 将任务与检测结果关联
#             defaults={'status': 'in_progress'}
#         )
#
#         if not created:
#             detection_result.status = 'in_progress'
#             detection_result.save()
#
#         # 提交AI检测任务给Celery，传递参数
#         run_ai_detection.delay(detection_result.id, cmd_block_size, urn_k, if_use_llm)
#
#     return Response({
#         "message": "Detection request submitted successfully",
#         "task_id": detection_task.id,
#         "task_name": detection_task.task_name,  # 返回任务名称
#     })


from pathlib import Path
import time
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_detection2(request):
    submit_time = time.time()
    user_id = request.user.id
    mode = int(request.data['mode'])
    user = User.objects.get(id=user_id)
    organization = user.organization  # 获取用户所属组织
    organization.reset_usage()  # 重置组织内所有用户的共享次数
    if not user.has_permission('submit'):
        return Response({"错误": "该用户没有提交检测的权限"}, status=403)

    # 获取用户提交的图像ID列表
    image_ids = request.data.get('image_ids', [])
    image_ids.sort()
    task_name = request.data.get('task_name', 'New Detection Task')  # 从请求中获取任务名称，默认为 "New Detection Task"

    # 获取额外的参数
    cmd_block_size = request.data.get('cmd_block_size', 64)  # 默认为64
    urn_k = request.data.get('urn_k', 0.3)  # 默认为0.3
    if_use_llm = request.data.get('if_use_llm', False)  # 默认为False
    if mode == 3:
        if_use_llm = True

    if not image_ids:
        return Response({"message": "No image IDs provided"}, status=400)

    # 查找用户上传的所有图像
    image_uploads = ImageUpload.objects.filter(id__in=image_ids, file_management__user=request.user)

    # 检验不为空
    if not image_uploads.exists():
        return Response({"message": "No valid images found"}, status=404)

    num_images = len(image_uploads)
    # 检查剩余次数是否足够
    if if_use_llm:
        if not organization.can_use_llm(num_images):
            return Response({
                                "message": f"You have exceeded your LLM method usage limit for this week. Your organization can only submit {organization.remaining_llm_uses} more images."},
                            status=400)
        # 使用 LLM 方法时，减少组织的 LLM 方法剩余次数
        organization.decrement_llm_uses(num_images)
    else:
        if not organization.can_use_non_llm(num_images):
            return Response({
                                "message": f"You have exceeded your non-LLM method usage limit for this week. Your organization can only submit {organization.remaining_non_llm_uses} more images."},
                            status=400)
        # 使用非 LLM 方法时，减少组织的非 LLM 方法剩余次数
        organization.decrement_non_llm_uses(num_images)

    # 创建一个新的检测任务
    detection_task = DetectionTask.objects.create(
        organization=user.organization,
        user=request.user,
        task_name=task_name,  # 使用用户提交的任务名称
        status='pending',  # 初始状态为"排队中"
        cmd_block_size=cmd_block_size,
        urn_k=urn_k,
        if_use_llm=if_use_llm
    )

    # 在Log表中记录检测任务的创建
    Log.objects.create(
        user=request.user,
        operation_type='detection',
        related_model='DetectionTask',
        related_id=detection_task.id
    )

    # ----① 建 DetectionResult，与原逻辑相同-------------
    detection_results = []          # 用来分批
    for image_upload in image_uploads:
        dr, _ = DetectionResult.objects.get_or_create(
            image_upload=image_upload,
            detection_task=detection_task,
            defaults={'status': 'in_progress'}
        )
        dr.status = 'in_progress'
        dr.save(update_fields=['status'])
        detection_results.append(dr)

    # ----② 20 张一批，写 zip & 调 Celery ---------------
    # views.py 片段（其余保持不变）
    temp_root = Path(settings.MEDIA_ROOT) / 'temp'
    temp_root.mkdir(parents=True, exist_ok=True)

    batch_size = 20
    for idx in range(0, len(detection_results), batch_size):
        batch_drs = detection_results[idx: idx + batch_size]

        # ——— ① 为该批创建专属子目录 temp/task_<task_id>_batch_<n>/ ———
        batch_dir = temp_root / f"task_{detection_task.id}_batch_{idx // batch_size}"
        batch_dir.mkdir(parents=True, exist_ok=True)

        zip_path = batch_dir / "img.zip"  # 固定文件名
        json_path = batch_dir / "data.json"  # 固定文件名

        # ——— ② 写 img.zip ———
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 先排序，根据 image_upload.id 的整数值排序
            sorted_drs = sorted(batch_drs, key=lambda dr: dr.image_upload.id)

            for dr in sorted_drs:
                src = dr.image_upload.image.path
                arcname = f"{int(dr.image_upload.id):08d}{Path(src).suffix}"
                zf.write(src, arcname=arcname)
            # for dr in batch_drs:
            #     src = dr.image_upload.image.path
            #     arcname = f"{dr.image_upload.id}{Path(src).suffix}"
            #     zf.write(src, arcname=arcname)

        # ——— ③ 写 data.json ———
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {"cmd_block_size": cmd_block_size, "urn_k": urn_k, "if_use_llm": if_use_llm},
                f, ensure_ascii=False, indent=4
            )

        # ——— ④ 调 Celery ———
        celery_time = time.time()
        print('从提交到调用celery耗时', celery_time - submit_time)
        # run_ai_detection_batch.delay(
        #     [dr.id for dr in batch_drs],
        #     str(batch_dir),  # 只传目录，任务里再拼 img.zip/data.json
        #     len(image_ids)
        # )
        if mode == 2:  # 加急
            pri = 0
        else:
            pri = 1
        fetch_batch.apply_async(
            args=[[dr.id for dr in batch_drs], str(batch_dir), len(image_ids), detection_task.pk],
            queue='ai',
            priority=pri
        )
        # fetch_batch(
        #     [dr.id for dr in batch_drs], str(batch_dir), len(image_ids), detection_task.pk
        # )

    return Response({
        "message": "Detection request submitted successfully",
        "task_id": detection_task.id,
        "task_name": detection_task.task_name,
    })


import os
from django.http import FileResponse
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..models import DetectionTask

from ..utils.report_generator import generate_detection_task_report

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_task_report(request, task_id):
    """
    GET /api/tasks/<task_id>/report/
    下载检测报告 PDF
    """
    try:
        task = DetectionTask.objects.get(id=task_id, user=request.user)
        # generate_detection_task_report(task)
    except DetectionTask.DoesNotExist:
        return Response({"detail": "Task not found."}, status=404)

    if task.status != "completed":
        return Response({"detail": "Task not completed yet."}, status=400)

    if not task.report_file:
        # generate_detection_task_report(task)
        return Response({"detail": "Report is still being generated."}, status=202)

    abs_path = os.path.join(settings.MEDIA_ROOT, task.report_file.name)
    if not os.path.exists(abs_path):
        return Response({"detail": "Report file missing."}, status=410)

    return FileResponse(open(abs_path, "rb"),
                        as_attachment=True,
                        filename=f"task_{task.id}_report.pdf")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def image2dr(request, image_id):
    """
    GET /api/images/<image_id>/getdr/
    下载该图片对应任务的检测报告 PDF
    """
    try:
        detection_result = DetectionResult.objects.select_related('detection_task').get(
            image_upload_id=image_id,
        )
    except DetectionResult.DoesNotExist:
        return Response({"detail": "Image or task not found, or permission denied."}, status=404)
    except DetectionResult.MultipleObjectsReturned:
        return Response({"detail": "Multiple detection results found for this image."}, status=500)
    # 返回detection_result的id
    return Response({"detection_result_id": detection_result.id})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_image_report(request, image_id):
    """
    GET /api/images/<image_id>/report/
    下载该图片对应任务的检测报告 PDF
    """
    try:
        # 获取与image_id关联且属于当前用户的DetectionResult及其关联的DetectionTask
        detection_result = DetectionResult.objects.select_related('detection_task').get(
            image_upload_id=image_id,
            # detection_task__user=request.user
        )
    except DetectionResult.DoesNotExist:
        return Response({"detail": "Image or task not found, or permission denied."}, status=404)
    except DetectionResult.MultipleObjectsReturned:
        return Response({"detail": "Multiple detection results found for this image."}, status=500)

    task = detection_result.detection_task

    # 后续逻辑与原接口一致，检查任务状态和报告文件
    if task.status != "completed":
        return Response({"detail": "Task not completed yet."}, status=400)

    if not task.report_file:
        return Response({"detail": "Report is still being generated."}, status=202)

    abs_path = os.path.join(settings.MEDIA_ROOT, task.report_file.name)
    if not os.path.exists(abs_path):
        return Response({"detail": "Report file missing."}, status=410)

    return FileResponse(open(abs_path, "rb"),
                        as_attachment=True,
                        filename=f"task_{task.id}_report.pdf")


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ..models import DetectionTask
from ..utils.serializers_safe import serialize_value

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_task_results(request, task_id):
    """
    ?include_image=1   —— 额外返回原始图像 URL
    """
    task = get_object_or_404(DetectionTask, id=task_id, user=request.user)

    include_img = request.query_params.get("include_image", "0") in ("1", "true", "True")
    result_list = []

    for dr in task.detection_results.select_related("image_upload"):
        item = {"result_id": dr.id, "image_id": dr.image_upload.id, "timestamp": dr.detection_time}
        if include_img:
            item["image_url"] = serialize_value(dr.image_upload.image, request)
        result_list.append(item)

    return Response({
        "task_id": task.id,
        "total_results": len(result_list),
        "results": result_list,
    })

# 增加两个接口，分别返回造假的图片，和正常的图片；判别方式是detection_result.is_fake
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_fake_task_results(request, task_id):
    """
    ?include_image=1   —— 额外返回原始图像 URL
    """
    task = get_object_or_404(DetectionTask, id=task_id, user=request.user)

    include_img = request.query_params.get("include_image", "0") in ("1", "true", "True")
    result_list = []

    for dr in task.detection_results.select_related("image_upload"):
        if dr.is_fake:
            item = {"result_id": dr.id, "image_id": dr.image_upload.id, "timestamp": dr.detection_time}
            if include_img:
                item["image_url"] = serialize_value(dr.image_upload.image, request)
            result_list.append(item)

    return Response({
        "task_id": task.id,
        "total_results": len(result_list),
        "results": result_list,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_normal_task_results(request, task_id):
    """
    ?include_image=1   —— 额外返回原始图像 URL
    """
    task = get_object_or_404(DetectionTask, id=task_id, user=request.user)

    include_img = request.query_params.get("include_image", "0") in ("1", "true", "True")
    result_list = []

    for dr in task.detection_results.select_related("image_upload"):
        if not dr.is_fake:
            item = {"result_id": dr.id, "image_id": dr.image_upload.id, "timestamp": dr.detection_time}
            if include_img:
                item["image_url"] = serialize_value(dr.image_upload.image, request)
            result_list.append(item)

    return Response({
        "task_id": task.id,
        "total_results": len(result_list),
        "results": result_list,
    })


from rest_framework import serializers
from ..models import DetectionResult, SubDetectionResult
from django.db.models.fields.files import FieldFile

class SubDetectionResultSerializer(serializers.ModelSerializer):
    mask_image   = serializers.SerializerMethodField()
    mask_matrix  = serializers.SerializerMethodField()   # ← 新增

    class Meta:
        model  = SubDetectionResult
        fields = ["method", "probability", "mask_image", "mask_matrix"]

    # --- helpers ---------------------------------------------------------
    def get_mask_image(self, obj):
        req = self.context["request"]
        if isinstance(obj.mask_image, FieldFile) and obj.mask_image:
            return req.build_absolute_uri(obj.mask_image.url)
        return None

    def get_mask_matrix(self, obj):
        """
        只有调用方在 context 里显式标记 include_matrix=True 时才返回
        """
        if self.context.get("include_matrix"):
            return obj.mask_matrix          # 已经是 list[list[float]]
        return None


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ..models import DetectionResult
from ..utils.serializers_safe import serialize_value

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detection_result_detail(request, result_id):
    dr = get_object_or_404(
        DetectionResult,
        id=result_id,
        # image_upload__file_management__user=request.user
    )

    # -------- 解析 fields & include_matrix ------------------------------
    raw_fields = request.query_params.get("fields")
    requested  = ({f.strip() for f in raw_fields.split(",")} if raw_fields
                  else {"overall", "llm", "llm_image", "ela_image", "exif", "timestamps",
                        "image", "sub_methods"})

    want_matrix = request.query_params.get("include_matrix", "0").lower() in ("1", "true", "yes")

    # -------- 基础信息 ---------------------------------------------------
    data = {"result_id": dr.id}

    def add(name, value):
        if name in requested:
            data[name] = value

    add("overall", {
        "is_fake": dr.is_fake,
        "confidence_score": dr.confidence_score,
    })
    add("llm",          dr.llm_judgment)
    add("llm_image",    serialize_value(dr.llm_image, request))
    add("ela_image",    serialize_value(dr.ela_image, request))
    add("exif", {
        "photoshop_edited":  dr.exif_photoshop,
        "time_modified":     dr.exif_time_modified,
    })
    add("timestamps",   timezone.localtime(dr.detection_time))
    add("image",        serialize_value(dr.image_upload.image, request))

    # -------- 子方法 -----------------------------------------------------
    if "sub_methods" in requested:
        subs = dr.sub_results.all()
        ser  = SubDetectionResultSerializer(
            subs,
            many=True,
            context={"request": request, "include_matrix": want_matrix}
        )
        data["sub_methods"] = ser.data

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detection_result_by_image(request, image_id):
    # 通过image_id获取对应的DetectionResult
    dr = get_object_or_404(
        DetectionResult,
        image_upload__id=image_id,
        # image_upload__file_management__user=request.user
    )

    # -------- 解析 fields & include_matrix ------------------------------
    raw_fields = request.query_params.get("fields")
    requested = ({f.strip() for f in raw_fields.split(",")} if raw_fields
                 else {"overall", "llm", "ela_image", "exif", "timestamps",
                       "image", "sub_methods"})

    want_matrix = request.query_params.get("include_matrix", "0").lower() in ("1", "true", "yes")

    # -------- 基础信息 ---------------------------------------------------
    data = {"result_id": dr.id}

    def add(name, value):
        if name in requested:
            data[name] = value

    add("overall", {
        "is_fake": dr.is_fake,
        "confidence_score": dr.confidence_score,
    })
    add("llm", dr.llm_judgment)
    add("ela_image", serialize_value(dr.ela_image, request))
    add("exif", {
        "photoshop_edited": dr.exif_photoshop,
        "time_modified": dr.exif_time_modified,
    })
    add("timestamps", dr.detection_time)
    add("image", serialize_value(dr.image_upload.image, request))

    # -------- 子方法 -----------------------------------------------------
    if "sub_methods" in requested:
        subs = dr.sub_results.all()
        ser = SubDetectionResultSerializer(
            subs,
            many=True,
            context={"request": request, "include_matrix": want_matrix}
        )
        data["sub_methods"] = ser.data

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_detection_task_status_normal(request, task_id):
    try:
        # 获取任务和关联的检测结果
        detection_task = DetectionTask.objects.get(id=task_id)
        detection_results = DetectionResult.objects.filter(detection_task=detection_task)

        # 收集任务相关的图像和状态信息
        task_status = {
            "task_id": detection_task.id,
            "task_name": detection_task.task_name,
            "status": detection_task.status,
            "upload_time": timezone.localtime(detection_task.upload_time),
            "completion_time": timezone.localtime(detection_task.completion_time),
            "detection_results": []
        }

        for result in detection_results:
            task_status["detection_results"].append({
                "image_id": result.image_upload.id,
                "status": result.status,
                "is_fake": result.is_fake,
                "confidence_score": result.confidence_score,
                "detection_time": timezone.localtime(result.detection_time),
            })

        return Response(task_status)

    except DetectionTask.DoesNotExist:
        return Response({"message": "Detection task not found"}, status=404)

from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 10  # 默认每页条数
    page_size_query_param = 'page_size'  # 客户端控制每页数量的参数名
    max_page_size = 100  # 允许客户端设置的最大每页数量

    def get_paginated_response(self, data):
        return Response({
            'page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'total': self.page.paginator.count,
            'tasks': data
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_tasks(request):
    # 获取分页参数
    page = int( request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 10))
    status = request.query_params.get('status', '')
    start_time = request.query_params.get('startTime', None)
    end_time = request.query_params.get('endTime', None)

    # 获取当前用户的所有检测任务并应用筛选条件
    tasks = DetectionTask.objects.filter(user=request.user).order_by('-upload_time')
    
    if status:
        tasks = tasks.filter(status=status)
    if start_time:
        tasks = tasks.filter(upload_time__gte=start_time)
    if end_time:
        tasks = tasks.filter(upload_time__lte=end_time)

    paginator = Paginator(tasks, page_size)

    try:
        page_obj = paginator.page(page)
    except Exception:
        return Response({'error': 'Invalid page number'}, status=400)

    task_data = [
        {
            'task_id': task.id,
            'task_name': task.task_name,
            'upload_time': timezone.localtime(task.upload_time).strftime('%Y-%m-%d %H:%M:%S'),
            'status': task.status,
            'completion_time': timezone.localtime(task.completion_time).strftime('%Y-%m-%d %H:%M:%S') if task.completion_time else None
        } for task in page_obj.object_list
    ]

    return Response({
        'tasks': task_data,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'total_tasks': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_tasks_depr(request):
    # 获取当前用户的所有检测任务
    detection_tasks = DetectionTask.objects.filter(user=request.user)
    task_list = []
    for task in detection_tasks:
        task_list.append({
            "task_id": task.id,
            "task_name": task.task_name,
            "status": task.status,
            "upload_time": timezone.localtime(task.upload_time),
            "completion_time": timezone.localtime(task.completion_time) if task.completion_time else None,
        })
    return Response(task_list)


from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated           # 如需鉴权
from rest_framework.response import Response
from rest_framework import status

from ..models import (
    DetectionTask, ReviewRequest, ManualReview,
    DetectionResult, SubDetectionResult
)

class DetectionTaskDeleteView(APIView):
    """
    按 task_id 删除检测任务及其所有衍生数据
    仅当任务状态为 'completed' 时允许删除
    """
    permission_classes = [IsAuthenticated]     # 可根据需要替换／删去

    def delete(self, request, task_id, *args, **kwargs):
        try:
            task = DetectionTask.objects.get(pk=task_id)
        except DetectionTask.DoesNotExist:
            return Response(
                {"detail": "任务不存在"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 只能删除 status == completed 的任务
        if task.status != "completed":
            return Response(
                {"detail": "检测尚未完成，无法删除"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ⚠️ 若只允许本人或管理员删除，可在此再做一次权限校验
        # if request.user != task.user and not request.user.is_staff:
        #     return Response({"detail": "无权限"}, status=status.HTTP_403_FORBIDDEN)

        # 原子事务，确保要么全部删掉，要么回滚
        with transaction.atomic():

            # 1) 先删 ReviewRequest 及人工审核链路
            review_qs = ReviewRequest.objects.filter(
                detection_result__detection_task=task
            )
            ManualReview.objects.filter(review_request__in=review_qs).delete()
            review_qs.delete()

            # 2) 删 DetectionResult 及其子结果
            result_qs = DetectionResult.objects.filter(detection_task=task)
            SubDetectionResult.objects.filter(detection_result__in=result_qs).delete()
            result_qs.delete()

            # 3) 剩余对象（ImageUpload 等）全部由 on_delete=CASCADE 自动清理
            task.delete()

        # 成功：204 No Content（REST 删除的经典返回码）
        return Response(status=status.HTTP_204_NO_CONTENT)