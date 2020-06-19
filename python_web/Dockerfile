FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7 AS builds

WORKDIR /install
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt \
    && mkdir -p /install/lib/python3.7/site-packages \
    && cp -rp /usr/local/lib/python3.7/site-packages /install/lib/python3.7

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7
COPY --from=builds /install/lib /usr/local/lib
WORKDIR /app
COPY . /app
CMD ["python", "main.py"]