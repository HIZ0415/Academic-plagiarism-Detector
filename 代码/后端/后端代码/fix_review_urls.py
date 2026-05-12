p = 'core/urls.py'
c = open(p, encoding='utf-8').read()
# add import
if 'views_manual_review_adapter' not in c:
    c = c.replace("from .views import views_review, views_organization", "from .views import views_review, views_organization\nfrom .views.views_manual_review_adapter import create_manual_review_request, get_manual_review_by_detection_task")
# replace old routes or add new
old1 = "path('manual-review-requests/', views_review.create_review_task_with_admin_check"
old2 = "path('manual-review-requests/', create_manual_review_request"
new_routes = "    path('manual-review-requests/', create_manual_review_request, name='manual_review_requests_create'),\n    path('manual-review-requests/by-detection-task/', get_manual_review_by_detection_task, name='manual_review_requests_by_task'),\n"
if old1 in c:
    lines = c.split('\n')
    lines = [l for l in lines if 'manual-review-requests' not in l]
    c = '\n'.join(lines)
if 'manual-review-requests/' not in c:
    c = c.rstrip()
    last = c.rfind(']')
    c = c[:last] + '\n' + new_routes + c[last:]
open(p, 'w', encoding='utf-8').write(c)
print('done')
