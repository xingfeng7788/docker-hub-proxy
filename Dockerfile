FROM python:3.12-slim

WORKDIR /app

# 安装 openssl 用于自动生成证书
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt -i  https://mirrors.aliyun.com/pypi/simple/

COPY . .

ENV HOST=0.0.0.0
ENV HTTP_PORT=8000
ENV HTTPS_PORT=8443
ENV SSL_KEYFILE=/app/certs/key.pem
ENV SSL_CERTFILE=/app/certs/cert.pem

EXPOSE 8000
EXPOSE 8443

RUN chmod +x start.sh
CMD ["bash", "start.sh"]
