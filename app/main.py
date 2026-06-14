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

if __name__ == "__main__":
    import uvicorn
    import os
    from app.config import config
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=debug_mode, workers=config.WORKERS)
