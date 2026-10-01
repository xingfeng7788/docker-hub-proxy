import os
from pathlib import Path
from dotenv import load_dotenv

# Load local settings before Config is evaluated; environment variables take priority.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

class Config:
    # Admin UI Auth
    ADMIN_USER = os.getenv("ADMIN_USER", "")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "")

    # Server Config
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    PROXY_PORT = int(os.getenv("PROXY_PORT", 8443))
    PROXY_URL = os.getenv("PROXY_URL", "https://mirror.aibety.com:8443").rstrip("/")
    WORKERS = int(os.getenv("WORKERS", 2))
    SSL_CERTFILE = os.getenv("SSL_CERTFILE", "./certs/fullchain.pem").strip()
    SSL_KEYFILE = os.getenv("SSL_KEYFILE", "./certs/privkey.pem").strip()
    SSL_KEYFILE_PASSWORD = os.getenv("SSL_KEYFILE_PASSWORD") or None
    # Proxy Config
    PROXY_TIMEOUT = float(os.getenv("PROXY_TIMEOUT", 10.0))

    # Access Control
    # IP Whitelist (comma separated)
    IP_WHITELIST = os.getenv("IP_WHITELIST", "")
    
    # Image Whitelist/Blacklist (regex strings)
    IMAGE_WHITELIST_REGEX = os.getenv("IMAGE_WHITELIST_REGEX", "")
    IMAGE_BLACKLIST_REGEX = os.getenv("IMAGE_BLACKLIST_REGEX", "")

    @classmethod
    def get_ssl_options(cls):
        if bool(cls.SSL_CERTFILE) != bool(cls.SSL_KEYFILE):
            raise ValueError("SSL_CERTFILE and SSL_KEYFILE must be configured together")
        if not cls.SSL_CERTFILE:
            return {}
        for name in ("SSL_CERTFILE", "SSL_KEYFILE"):
            if not Path(getattr(cls, name)).is_file():
                raise ValueError(f"{name} does not point to a file: {getattr(cls, name)}")
        return {
            "ssl_certfile": cls.SSL_CERTFILE,
            "ssl_keyfile": cls.SSL_KEYFILE,
            "ssl_keyfile_password": cls.SSL_KEYFILE_PASSWORD,
        }
    
    @classmethod
    def get_ip_whitelist(cls):
        if not cls.IP_WHITELIST:
            return []
        return [ip.strip() for ip in cls.IP_WHITELIST.split(",") if ip.strip()]

config = Config()
