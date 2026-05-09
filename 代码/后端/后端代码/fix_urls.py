import re
p = 'core/urls.py'
c = open(p, encoding='utf-8').read()

# 添加 manual-review-requests/ 路由别名
new_routes = """
    # 前端兼容路由 - manual-review-requests
    path('manual-review-requests/', views_review.create_review_task_with_admin_check, name='manual_review_requests_create'),
    path('manual-review-requests/by-detection-task/', views_review.get_publisher_review_tasks, name='manual_review_requests_by_task'),
"""

if 'manual-review-requests/' not in c:
    # 插入到 urlpatterns 的末尾（最后一个 ] 之前）
    c = c.rstrip()
    last_bracket = c.rfind(']')
    c = c[:last_bracket] + new_routes + c[last_bracket:]
    open(p, 'w', encoding='utf-8').write(c)
    print('added routes')
else:
    print('already exists')
