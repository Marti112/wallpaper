import requests
url = 'http://172.17.207.112:5678/image'
files = {'media': open('3.jpg', 'rb')}
print(requests.post(url, files=files).content)