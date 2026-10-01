#!/bin/sh
# Download the project's shared self-signed certificate set from GitHub.
set -eu
umask 077

if [ "$#" -gt 1 ]; then
    printf 'Usage: sh download-certs.sh [certificate-directory]\n' >&2
    exit 1
fi

certs_dir=${1:-./certs}
certs_repo=${CERTS_GITHUB_REPO:-xingfeng7788/docker-hub-proxy}
certs_ref=${CERTS_GITHUB_REF:-master}
certs_base_url="https://raw.githubusercontent.com/$certs_repo/$certs_ref/certs"

for command_name in curl openssl cmp; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        printf 'Required command is missing: %s\n' "$command_name" >&2
        exit 1
    fi
done

mkdir -p -- "$certs_dir"
for cert_file in fullchain.pem privkey.pem ca.crt; do
    if [ -e "$certs_dir/$cert_file" ] || [ -L "$certs_dir/$cert_file" ]; then
        printf 'Refusing to overwrite existing file: %s/%s\n' "$certs_dir" "$cert_file" >&2
        printf 'Back up the current certificates or choose an empty directory.\n' >&2
        exit 1
    fi
done

download_dir=$(mktemp -d "$certs_dir/.download.XXXXXX")
trap 'rm -rf -- "$download_dir"' 0
trap 'exit 1' HUP INT TERM

for cert_file in fullchain.pem privkey.pem ca.crt; do
    curl -fL --retry 2 --connect-timeout 10 --max-time 60 \
        -o "$download_dir/$cert_file" "$certs_base_url/$cert_file"
done

# Validate expiry, the public key pair, and the self-signed trust copy before installation.
openssl x509 -in "$download_dir/fullchain.pem" -checkend 0 -noout
openssl x509 -in "$download_dir/fullchain.pem" -pubkey -noout |
    openssl pkey -pubin -pubout -out "$download_dir/certificate.pub"
openssl pkey -in "$download_dir/privkey.pem" -passin pass: -pubout \
    -out "$download_dir/private-key.pub"
if ! cmp -s "$download_dir/certificate.pub" "$download_dir/private-key.pub"; then
    printf 'The downloaded certificate and private key do not match.\n' >&2
    exit 1
fi
if ! cmp -s "$download_dir/fullchain.pem" "$download_dir/ca.crt"; then
    printf 'The self-signed ca.crt copy does not match fullchain.pem.\n' >&2
    exit 1
fi

chmod 600 "$download_dir/privkey.pem"
chmod 644 "$download_dir/fullchain.pem" "$download_dir/ca.crt"
for cert_file in fullchain.pem privkey.pem ca.crt; do
    mv -- "$download_dir/$cert_file" "$certs_dir/$cert_file"
done

printf 'Certificates installed in %s\n' "$certs_dir"
openssl x509 -in "$certs_dir/fullchain.pem" -noout -subject -enddate
printf 'This private key is public in GitHub. Use this certificate set for testing only.\n'
