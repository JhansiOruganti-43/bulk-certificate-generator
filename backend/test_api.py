import requests
import json

payload = {
    'recipients': [
        {'recipient_name': 'Test User Batch', 'recipient_email': 'testbat@example.com', 'course_name': 'Test course 2'}
    ]
}
resp = requests.post('http://localhost:8000/api/batches/', json=payload)
print("Batch Create Reps:", resp.json())
batch_id = resp.json()['id']

certs = requests.get(f'http://localhost:8000/api/batches/{batch_id}/certificates').json()
print("Certs array:", certs)

if len(certs) > 0 and certs[0]['status'] == 'completed':
    pdf_resp = requests.get(f'http://localhost:8000/api/certificates/{certs[0]["id"]}/download')
    print('PDF Content-Type:', pdf_resp.headers.get('Content-Type'))
    print('PDF Size (bytes):', len(pdf_resp.content))
    with open('test_cert.pdf', 'wb') as f:
        f.write(pdf_resp.content)
