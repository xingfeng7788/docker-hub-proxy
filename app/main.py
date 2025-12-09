from fastapi import FastAPI
from app.database import create_db_and_tables, upgrade_db
from app.services import proxy_manager
from app.routers import web_ui, docker_proxy
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Database...")
    create_db_and_tables()
    upgrade_db() # Run migrations
    
    logger.info("Seeding Proxies...")
    proxy_manager.init_proxies()
    
    logger.info("Starting Speed Test Scheduler...")
    scheduler.add_job(proxy_manager.run_speed_test, 'interval', minutes=60)
    scheduler.add_job(proxy_manager.fetch_and_update_proxies, 'interval', minutes=60)
    scheduler.start()
    
    # Run initial speed test
    scheduler.add_job(proxy_manager.run_speed_test)
    
    yield
    
    # Shutdown
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan, title="Docker Hub Proxy")

# Mount Routers
app.include_router(web_ui.router)
app.include_router(docker_proxy.router)

def ensure_certs():
    cert_dir = "certs"
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
    
    cert_path = os.path.join(cert_dir, "cert.pem")
    key_path = os.path.join(cert_dir, "key.pem")
    
    if not os.path.exists(cert_path) or not os.path.exists(key_path):
        logger.info("Generating self-signed SSL certificates...")
        try:
            subprocess.run([
                "openssl", "req", "-x509", "-newkey", "rsa:4096", 
                "-keyout", key_path, "-out", cert_path, 
                "-days", "365", "-nodes", 
                "-subj", "/CN=localhost"
            ], check=True, capture_output=True)
            logger.info(f"Certificates generated at {cert_dir}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate certificates: {e}")
            raise
            
    return cert_path, key_path

if __name__ == "__main__":
    import uvicorn
    import asyncio
    import os
    import subprocess
    
    # Generate certs
    cert_file, key_file = ensure_certs()
    
    # Configure servers
    # HTTP Server (UI)
    config_http = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    
    # HTTPS Server (Proxy)
    config_https = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=8443, 
        ssl_keyfile=key_file, 
        ssl_certfile=cert_file,
        log_level="info"
    )
    
    server_http = uvicorn.Server(config_http)
    server_https = uvicorn.Server(config_https)
    
    async def run_servers():
        logger.info("Starting HTTP server on port 8000 (Web UI)...")
        logger.info("Starting HTTPS server on port 8443 (Docker Proxy)...")
        await asyncio.gather(
            server_http.serve(),
            server_https.serve()
        )
    
    asyncio.run(run_servers())
