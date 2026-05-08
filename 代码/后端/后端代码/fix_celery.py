p = 'fake_image_detector/settings.py'
lines = open(p, encoding='utf-8').readlines()
clean = [l for l in lines if 'CELERY_TASK_ALWAYS_EAGER' not in l and 'CELERY_TASK_EAGER_PROPAGATES' not in l and 'CELERY_BROKER_URL' not in l and 'CELERY_RESULT_BACKEND' not in l]
clean.append('\nCELERY_TASK_ALWAYS_EAGER = True\n')
clean.append('CELERY_TASK_EAGER_PROPAGATES = True\n')
clean.append("CELERY_BROKER_URL = 'memory://'\n")
clean.append("CELERY_RESULT_BACKEND = 'cache+memory://'\n")
open(p, 'w', encoding='utf-8').writelines(clean)
print('done')
