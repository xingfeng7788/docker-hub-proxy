FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i  https://mirrors.aliyun.com/pypi/simple/

COPY . .

ENV HOST=0.0.0.0
ENV PORT=8000
ENV PROXY_PORT=8443
ENV WORKERS=2

EXPOSE 8000 8443

CMD ["python", "-m", "app.main"]
