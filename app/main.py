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

def initialize_database():
    logger.info("Initializing Database...")
    create_db_and_tables()
    upgrade_db() # Run migrations
    
    logger.info("Seeding Proxies...")
    proxy_manager.init_proxies()


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    logger.info("Starting Speed Test Scheduler...")
    scheduler.add_job(proxy_manager.run_speed_test, 'interval', minutes=60)
    scheduler.add_job(proxy_manager.fetch_and_update_proxies, 'interval', minutes=60)
    scheduler.start()
    
    # Run initial speed test
    scheduler.add_job(proxy_manager.run_speed_test)
    
    yield
    
    # Shutdown
    scheduler.shutdown()

@asynccontextmanager
async def proxy_lifespan(app: FastAPI):
    initialize_database()
    yield


web_app = FastAPI(lifespan=lifespan, title="Docker Hub Proxy Manager")
web_app.include_router(web_ui.router)

app = FastAPI(lifespan=proxy_lifespan, title="Docker Hub Proxy")
app.include_router(docker_proxy.router)

def run(service="proxy"):
    import uvicorn
    import os
    from app.config import config
    if service not in ("web", "proxy"):
        raise ValueError("service must be web or proxy")
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    uvicorn.run(
        "app.main:web_app" if service == "web" else "app.main:app",
        host=config.HOST,
        port=config.PORT if service == "web" else config.PROXY_PORT,
        reload=debug_mode,
        workers=1 if service == "web" else config.WORKERS,
        **({} if service == "web" else config.get_ssl_options()),
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Docker Hub Proxy services")
    parser.add_argument("--service", choices=("web", "proxy"), default="proxy")
    run(parser.parse_args().service)
