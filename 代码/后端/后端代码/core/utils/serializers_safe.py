# utils/serializers_safe.py
from django.db.models.fields.files import FieldFile

def serialize_value(value, request):
    """
    - File/ImageField → 完整 URL
    - 其他 → 原样返回（必须是 JSON 可序列化的原生类型）
    """
    if isinstance(value, FieldFile):
        if not value or not value.url:
            return None
        return request.build_absolute_uri(value.url) if request is not None else value.url
    return value
