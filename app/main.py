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

# We attach lifespan to the proxy_app, which handles the background tasks
proxy_app = FastAPI(lifespan=lifespan, title="Docker Hub Proxy")
proxy_app.include_router(docker_proxy.router)

web_app = FastAPI(title="Docker Hub Proxy Web UI")
web_app.include_router(web_ui.router)

if __name__ == "__main__":
    import uvicorn
    import os
    import asyncio
    from app.config import config
    
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    
    async def serve():
        http_config = uvicorn.Config(
            app=web_app, 
            host=config.HOST, 
            port=config.HTTP_PORT,
            reload=debug_mode
        )
        http_server = uvicorn.Server(http_config)
        
        https_config = uvicorn.Config(
            app=proxy_app, 
            host=config.HOST, 
            port=config.HTTPS_PORT,
            ssl_keyfile=config.SSL_KEYFILE if config.SSL_KEYFILE else None,
            ssl_certfile=config.SSL_CERTFILE if config.SSL_CERTFILE else None,
            reload=debug_mode
        )
        https_server = uvicorn.Server(https_config)
        
        await asyncio.gather(
            http_server.serve(),
            https_server.serve()
        )
        
    asyncio.run(serve())
