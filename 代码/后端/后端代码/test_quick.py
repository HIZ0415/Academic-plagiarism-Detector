import requests
BASE = 'http://127.0.0.1:8000'
r = requests.post(f'{BASE}/api/login/', json={'email':'publisher_test@example.com','password':'Test123456','role':'publisher'})
h = {'Authorization': 'Bearer ' + r.json()['access']}
print('[1] Login OK')
body = {'task_name':'test-review','text':'This paper presents an interesting approach. The methodology is sound. However the evaluation could be more comprehensive.'}
rv = requests.post(f'{BASE}/api/review/submit/', json=body, headers=h)
print(f'[2] Review submit: {rv.status_code} {rv.json()}')
tid = rv.json()['task_id']
st = requests.get(f'{BASE}/api/review/tasks/{tid}/status/', headers=h)
print(f'[3] Status: {st.json()}')
res = requests.get(f'{BASE}/api/review/{tid}/result/', headers=h)
print(f'[4] Result: {res.status_code} {res.json()}')
