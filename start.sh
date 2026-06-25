#!/bin/bash

CERT_DIR="/app/certs"
mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_DIR/key.pem" ] || [ ! -f "$CERT_DIR/cert.pem" ]; then
    echo "SSL certificates not found. Generating self-signed certificates..."
    
    if [ -n "$CERT_HOSTNAME" ]; then
        # 判断是否为 IP 地址
        if [[ $CERT_HOSTNAME =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 3650 -nodes -subj "/CN=$CERT_HOSTNAME" -addext "subjectAltName=IP:$CERT_HOSTNAME"
        else
            openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 3650 -nodes -subj "/CN=$CERT_HOSTNAME" -addext "subjectAltName=DNS:$CERT_HOSTNAME"
        fi
    else
        openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 3650 -nodes -subj "/CN=docker-hub-proxy"
    fi
    
    echo "Self-signed certificates generated successfully."
fi

python -m app.main
