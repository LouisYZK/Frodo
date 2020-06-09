from fastapi import FastAPI
from models import Post
import threading
test_app = FastAPI()
import requests

url = 'http://localhost:8001/user/search'
def task(i):
    data = requests.get(url, params={'name': i})
    return data.json()
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=10) as e:
    tasks = [e.submit(task(i)) for i in 'xascsafdfdasdsdwd']

for r in as_completed(tasks):
    print(r.result())
    