import os
import re

class Config:
    # Admin UI Auth
    ADMIN_USER = os.getenv("ADMIN_USER", "")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "")

    # Server Config
    HOST = os.getenv("HOST", "0.0.0.0")
    HTTP_PORT = int(os.getenv("HTTP_PORT", 8000))
    HTTPS_PORT = int(os.getenv("HTTPS_PORT", 8443))
    SSL_KEYFILE = os.getenv("SSL_KEYFILE", "")
    SSL_CERTFILE = os.getenv("SSL_CERTFILE", "")
    WORKERS = int(os.getenv("WORKERS", 2))
    # Proxy Config
    PROXY_TIMEOUT = float(os.getenv("PROXY_TIMEOUT", 10.0))

    # Access Control
    # IP Whitelist (comma separated)
    IP_WHITELIST = os.getenv("IP_WHITELIST", "")
    
    # Image Whitelist/Blacklist (regex strings)
    IMAGE_WHITELIST_REGEX = os.getenv("IMAGE_WHITELIST_REGEX", "")
    IMAGE_BLACKLIST_REGEX = os.getenv("IMAGE_BLACKLIST_REGEX", "")
    
    @classmethod
    def get_ip_whitelist(cls):
        if not cls.IP_WHITELIST:
            return []
        return [ip.strip() for ip in cls.IP_WHITELIST.split(",") if ip.strip()]

config = Config()
