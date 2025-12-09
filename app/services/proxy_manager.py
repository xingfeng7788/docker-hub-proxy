import asyncio
import logging
import httpx
from sqlmodel import Session, select
from app.database import engine
from app.models import ProxyNode
from datetime import datetime
from typing import Optional

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

async def fetch_and_update_proxies():
    """Fetch free proxies from external source and add them to DB."""
    url = "https://status.anye.xyz/status.json"
    logger.info(f"Fetching proxies from {url}...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch proxies: {response.status_code}")
                return

            data = response.json()
            added_count = 0
            
            with Session(engine) as session:
                existing_urls = {p.url for p in session.exec(select(ProxyNode)).all()}
                
                for item in data:
                    # Filter logic
                    is_valid = True
                    tags = item.get("tags", [])
                    for tag in tags:
                        tag_name = tag.get("name", "")
                        if "付费" in tag_name or "内网" in tag_name or "需登陆" in tag_name:
                            is_valid = False
                            break
                    
                    if not is_valid:
                        continue

                    node_url = item.get("url")
                    if not node_url:
                        continue
                        
                    # Normalize URL (remove trailing slash)
                    node_url = node_url.rstrip("/")
                    
                    # Check if exists (check against normalized existing urls)
                    if node_url in existing_urls or (node_url + "/") in existing_urls:
                        continue
                        
                    # Add new node
                    new_node = ProxyNode(
                        name=item.get("name", "Unknown Mirror"),
                        url=node_url,
                        registry_type="dockerhub", # Most of these are dockerhub mirrors
                        enabled=True
                    )
                    session.add(new_node)
                    existing_urls.add(node_url) # Prevent duplicates in same batch
                    added_count += 1
                
                session.commit()
            
            logger.info(f"Successfully added {added_count} new proxies.")

    except Exception as e:
        logger.error(f"Error fetching proxies: {e}")

async def run_speed_test():
    """Run speed test on all enabled proxies."""
    logger.info("Starting speed test...")
    with Session(engine) as session:
        proxies = session.exec(select(ProxyNode).where(ProxyNode.enabled == True)).all()
        
        for proxy in proxies:
            latency = await check_proxy_latency(proxy)
            proxy.latency = latency
            proxy.last_check = datetime.now()
            if latency >= 9999.0:
                proxy.enabled = False # Mark as disabled if timeout
            else:
                proxy.enabled = True # Re-enable if it comes back online
            session.add(proxy)
        
        session.commit()
    logger.info("Speed test completed.")

def get_best_proxy(path: str = "") -> tuple[Optional[ProxyNode], str]:
    """
    Get the best performing proxy node, accounting for route prefixes.
    Returns (node, adjusted_path).
    If a prefix is matched, it is stripped from the path.
    """
    path = path.lstrip("/")
    
    with Session(engine) as session:
        # Get all enabled proxies sorted by latency
        proxies = session.exec(select(ProxyNode).where(ProxyNode.enabled == True).where(ProxyNode.latency < 9999).order_by(ProxyNode.latency)).all()
        
        # 1. Try to find a specific prefix match
        # We look for the longest matching prefix to be specific
        best_match_node = None
        longest_prefix_len = -1
        
        for p in proxies:
            if p.route_prefix:
                # Normalize prefix: ensure no leading/trailing slashes for comparison
                prefix = p.route_prefix.strip("/")
                if path.startswith(prefix + "/"):
                    if len(prefix) > longest_prefix_len:
                        longest_prefix_len = len(prefix)
                        best_match_node = p
        
        if best_match_node:
            prefix = best_match_node.route_prefix.strip("/")
            # Strip prefix: "ghcr/foo/bar" -> "foo/bar"
            # path is "ghcr/foo/bar"
            # prefix len is 4.
            # slice from len+1 to skip the slash.
            adjusted_path = path[len(prefix)+1:]
            return best_match_node, adjusted_path

        # 2. Fallback to generic proxies (no prefix)
        for p in proxies:
            if not p.route_prefix:
                return p, path

        # 3. Fallback if nothing found but we have generic proxies?
        # The loop above handles it.
        
        # 4. Total fallback (no active nodes or only mismatched prefixes)
        # Create a temp node pointing to docker hub?
        return ProxyNode(name="Fallback Official", url="https://registry-1.docker.io"), path

def get_all_proxies():
    with Session(engine) as session:
        return session.exec(select(ProxyNode)).all()

def add_proxy(name: str, url: str, registry_type: str = "dockerhub", route_prefix: str = None, username: str = None, password: str = None):
    with Session(engine) as session:
        node = ProxyNode(name=name, url=url, registry_type=registry_type, route_prefix=route_prefix, username=username, password=password)
        session.add(node)
        session.commit()
        return node

def update_proxy(proxy_id: int, name: str, url: str, registry_type: str = "dockerhub", route_prefix: str = None, username: str = None, password: str = None):
    with Session(engine) as session:
        node = session.get(ProxyNode, proxy_id)
        if node:
            node.name = name
            node.url = url
            node.registry_type = registry_type
            node.route_prefix = route_prefix
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
