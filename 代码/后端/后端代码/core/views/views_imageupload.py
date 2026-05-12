from ..models import FileManagement, ImageUpload, Log, User
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from ..utils.image_preprocessing import (
    detect_upload_kind,
    preprocess_uploaded_image_resource,
    save_original_upload,
)

ALPHA_ALLOWED_IMAGE_EXT = {'.png', '.jpg', '.jpeg'}


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_file(request):
    user = User.objects.get(id=request.user.id)
    if not user.has_permission("upload"):
        return Response({"detail": "User does not have upload permission."}, status=403)

    # 获取上传的文件
    uploaded_file = request.FILES.get("file")
    if uploaded_file is None:
        return Response({"detail": "No file provided."}, status=400)

    file_name = uploaded_file.name
    file_size = uploaded_file.size
    file_type = uploaded_file.content_type
    raw_bytes = uploaded_file.read()
    try:
        detect_upload_kind(file_name, file_type, raw_bytes)
    except ValueError:
        return Response({"message": "Unsupported upload type."}, status=400)

    # 存储文件到 FileManagement 表
    file_management = FileManagement.objects.create(
        organization=user.organization,
        user=request.user,
        file_name=file_name,
        file_size=file_size,
        file_type=file_type
    )

    try:
        file_path = save_original_upload(file_name, raw_bytes, "uploads")
        image_count = preprocess_uploaded_image_resource(file_management, file_name, file_type, raw_bytes)
    except ValueError as exc:
        file_management.delete()
        return Response({"message": str(exc)}, status=400)

    # 在Log表中记录上传操作
    Log.objects.create(
        user=request.user,
        operation_type="upload",
        related_model="FileManagement",
        related_id=file_management.id,
    )

    return Response(
        {
            "message": "File uploaded successfully",
            "file_id": file_management.id,
            "file_url": f"/media/{file_path}",
            "image_count": image_count,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_file_details(request, file_id):
    try:
        file_management = FileManagement.objects.get(id=file_id, user=request.user)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    extracted_images = ImageUpload.objects.filter(file_management=file_management)
    image_urls = [image.image.url for image in extracted_images]
    is_pdf = file_management.file_type == "application/pdf"

    return Response(
        {
            "file_id": file_management.id,
            "user_id": file_management.user.id,
            "file_name": file_management.file_name,
            "file_url": file_management.file_size,
            "upload_time": timezone.localtime(file_management.upload_time),
            "is_pdf": is_pdf,
            "extracted_images": image_urls,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_extracted_images(request, file_id):
    try:
        file_management = FileManagement.objects.get(id=file_id, user=request.user)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    extracted_images = ImageUpload.objects.filter(file_management=file_management).order_by("-id")

    paginator = CustomPagination()
    paginated_images = paginator.paginate_queryset(extracted_images, request)

    image_list = []
    for image in paginated_images:
        image_list.append(
            {
                "image_id": image.id,
                "image_url": image.image.url,
                "page_number": image.page_number if image.extracted_from_pdf else None,
                "extracted_from_pdf": image.extracted_from_pdf,
                "isDetect": image.isDetect,
                "isReview": image.isReview,
                "isFake": image.isFake,
            }
        )

    return Response(
        {
            "file_id": file_management.id,
            "page": paginator.page.number,
            "page_size": paginator.get_page_size(request),
            "total": paginator.page.paginator.count,
            "images": image_list,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_file_tag(request, file_id):
    try:
        file = FileManagement.objects.get(id=file_id)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found."}, status=404)

    tag = request.data.get("tag")
    if tag not in [choice[0] for choice in FileManagement.TAG_CHOICES]:
        return Response({"message": "Invalid tag type."}, status=400)

    file.tag = tag
    file.save()

    return Response(
        {
            "message": "File add tag successfully",
            "file_id": file.id,
            "file_url": f"/media/{file.file_name}",
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def get_all_file_images(request, file_management_id):
    try:
        file_management = FileManagement.objects.get(id=file_management_id)
    except FileManagement.DoesNotExist:
        return Response({"message": "File not found"}, status=404)

    page = int(request.query_params.get("page", 1))
    page_size = min(int(request.query_params.get("page_size", 10)), 100)
    is_detect = request.query_params.get("isDetect")
    is_review = request.query_params.get("isReview")
    is_fake = request.query_params.get("isFake")

    images = ImageUpload.objects.filter(file_management=file_management)

    if is_detect in ["true", "True", "1"]:
        images = images.filter(isDetect=True)
    elif is_detect in ["false", "False", "0"]:
        images = images.filter(isDetect=False)

    if is_review in ["true", "True", "1"]:
        images = images.filter(isReview=True)
    elif is_review in ["false", "False", "0"]:
        images = images.filter(isReview=False)

    if is_fake in ["true", "True", "1"]:
        images = images.filter(isFake=True)
    elif is_fake in ["false", "False", "0"]:
        images = images.filter(isFake=False)

    paginator = Paginator(images, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        return Response({"error": "Page not found"}, status=404)

    results = []
    for image in page_obj.object_list:
        results.append(
            {
                "img_id": image.id,
                "img_url": image.image.url,
                "isDetect": image.isDetect,
                "isReview": image.isReview,
                "isFake": image.isFake,
            }
        )

    return Response(
        {
            "file_id": file_management_id,
            "imgs": results,
            "current_page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_count": paginator.count,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
    )
