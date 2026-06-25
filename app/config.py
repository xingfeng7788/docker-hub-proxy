import os
import re

class Config:
    # Admin UI Auth
    ADMIN_USER = os.getenv("ADMIN_USER", "")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "")

    # Server Config
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    WORKERS = int(os.getenv("WORKERS", 2))
    # Proxy Config
    PROXY_TIMEOUT = float(os.getenv("PROXY_TIMEOUT", 10.0))
    SEARCH_PROXY = os.getenv("SEARCH_PROXY", "")

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
