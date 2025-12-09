import asyncio
import logging
import httpx
from sqlmodel import Session, select
from app.database import engine
from app.models import ProxyNode
from datetime import datetime

logger = logging.getLogger("proxy_manager")

DEFAULT_PROXIES = [
    # {"name": "Docker Hub Official", "url": "https://registry-1.docker.io"},
    # {"name": "Google Mirror", "url": "https://mirror.gcr.io"},
    # Add more known public mirrors if appropriate, but many are region locked or require auth.
]

def init_proxies():
    """Seed default proxies if none exist."""
    with Session(engine) as session:
        statement = select(ProxyNode)
        results = session.exec(statement).all()
        if not results:
            for p in DEFAULT_PROXIES:
                node = ProxyNode(name=p["name"], url=p["url"], is_default=True)
                session.add(node)
            session.commit()

async def check_proxy_latency(node: ProxyNode):
    """Check latency for a single proxy node."""
    url = node.url.rstrip("/") + "/v2/"
    start = datetime.now()
    try:
        auth = None
        if node.username and node.password:
            auth = (node.username, node.password)

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, auth=auth) as client:
            # We don't need auth to just check connectivity, usually 401 is a good sign (it's alive).
            # But if we have credentials, we might get 200.
            response = await client.get(url)
            # 200 or 401 means it's a docker registry
            if response.status_code in [200, 401]:
                duration = (datetime.now() - start).total_seconds() * 1000
                return duration
            else:
                return 9999.0
    except Exception as e:
        # logger.warning(f"Proxy {node.name} failed: {e}")
        return 9999.0

async def run_speed_test():
    """Run speed test on all enabled proxies."""
    logger.info("Starting speed test...")
    with Session(engine) as session:
        proxies = session.exec(select(ProxyNode).where(ProxyNode.enabled == True)).all()
        
        for proxy in proxies:
            latency = await check_proxy_latency(proxy)
            proxy.latency = latency
            proxy.last_check = datetime.now()
            session.add(proxy)
        
        session.commit()
    logger.info("Speed test completed.")

def get_best_proxy() -> str:
    """Get the URL of the best performing proxy."""
    with Session(engine) as session:
        # Get enabled proxies sorted by latency
        # Filter out latency >= 9999
        statement = select(ProxyNode).where(ProxyNode.enabled == True).where(ProxyNode.latency < 9999).order_by(ProxyNode.latency)
        result = session.exec(statement).first()
        
        if result:
            return result.url
        
        # Fallback to official if everything fails
        return "https://registry-1.docker.io"

def get_all_proxies():
    with Session(engine) as session:
        return session.exec(select(ProxyNode)).all()

def add_proxy(name: str, url: str, username: str = None, password: str = None):
    with Session(engine) as session:
        node = ProxyNode(name=name, url=url, username=username, password=password)
        session.add(node)
        session.commit()
        return node

def update_proxy(proxy_id: int, name: str, url: str, username: str = None, password: str = None):
    with Session(engine) as session:
        node = session.get(ProxyNode, proxy_id)
        if node:
            node.name = name
            node.url = url
            node.username = username
            node.password = password
            session.add(node)
            session.commit()
            return node
        return None

def delete_proxy(proxy_id: int):
    with Session(engine) as session:
        node = session.get(ProxyNode, proxy_id)
        if node:
            session.delete(node)
            session.commit()
