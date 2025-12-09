FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i  https://mirrors.aliyun.com/pypi/simple/

COPY . .

EXPOSE 8000
EXPOSE 8443

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
