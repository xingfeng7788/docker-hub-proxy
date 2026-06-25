#!/bin/bash

CERT_DIR="/app/certs"
mkdir -p "$CERT_DIR"

if [ ! -f "$CERT_DIR/key.pem" ] || [ ! -f "$CERT_DIR/cert.pem" ]; then
    echo "SSL certificates not found. Generating self-signed certificates..."
    openssl req -x509 -newkey rsa:4096 -keyout "$CERT_DIR/key.pem" -out "$CERT_DIR/cert.pem" -days 3650 -nodes -subj "/CN=docker-hub-proxy"
    echo "Self-signed certificates generated successfully."
fi

python -m app.main
