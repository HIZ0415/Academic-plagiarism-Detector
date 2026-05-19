import requests
BASE='http://127.0.0.1:8000'
r=requests.post(f'{BASE}/api/login/',json={'email':'publisher_test@example.com','password':'Publisher123!','role':'publisher'})
h={'Authorization':'Bearer '+r.json()['access']}
print('[1] login OK')
rv=requests.post(f'{BASE}/api/review/submit/',json={'task_name':'report-test','text':'This paper presents a novel approach. The results are convincing.'},headers=h)
tid=rv.json()['task_id']
print(f'[2] submit OK, task_id={tid}')
st=requests.get(f'{BASE}/api/review/tasks/{tid}/status/',headers=h)
print('[3] status:', st.json()['status'])
dl=requests.get(f'{BASE}/api/tasks/{tid}/report/',headers=h)
print('[4] report:', dl.status_code)
if dl.status_code==200:
    open('report_test.pdf','wb').write(dl.content)
    print(f'    saved report_test.pdf ({len(dl.content)} bytes)')
else:
    print('    error:', dl.text[:200])
