p = 'fake_image_detector/local_settings.py'
c = open(p, encoding='utf-8').read()
if 'CELERY_TASK_ALWAYS_EAGER' not in c:
    c += '\nCELERY_TASK_ALWAYS_EAGER = True\nCELERY_TASK_EAGER_PROPAGATES = True\n'
    open(p, 'w', encoding='utf-8').write(c)
    print('added EAGER settings')
else:
    print('already exists')
