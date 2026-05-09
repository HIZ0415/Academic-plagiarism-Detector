p = 'core/views/views_manual_review_adapter.py'
c = open(p, encoding='utf-8-sig').read()
old = 'placeholder_image, _ = ImageUpload.objects.get_or_create(user=request.user, file_name="__placeholder__", defaults={"organization": user.organization, "file_size": 0, "file_type": "placeholder"})'
new = 'placeholder_image, _ = ImageUpload.objects.get_or_create(detection_task=task, defaults={"image": "placeholder.png"})'
c = c.replace(old, new)
open(p, 'w', encoding='utf-8').write(c)
print('fixed')
