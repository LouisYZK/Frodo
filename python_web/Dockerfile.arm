FROM --platform=linux/arm64 python:3.8

WORKDIR /code
COPY requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY . /code/app
WORKDIR /code/app
RUN mkdir -p /code/app/static/upload
CMD ["python", "main.py"]