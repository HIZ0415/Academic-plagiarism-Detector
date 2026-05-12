p = 'core/views/views_manual_review_adapter.py'
c = open(p, encoding='utf-8-sig').read()
c = c.replace('from .models import', 'from ..models import')
open(p, 'w', encoding='utf-8').write(c)
print('fixed')
