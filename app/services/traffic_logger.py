from datetime import date
from sqlmodel import Session, select, func
from app.database import engine
from app.models import TrafficStats, PullHistory, get_shanghai_time, ProxyNode

def log_traffic(bytes_downloaded: int = 0, bytes_uploaded: int = 0, node_id: int = None):
    today_str = get_shanghai_time().date().isoformat()
    with Session(engine) as session:
        statement = select(TrafficStats).where(TrafficStats.date == today_str)
        stats = session.exec(statement).first()
        
        if not stats:
            stats = TrafficStats(date=today_str)
        
        stats.download_bytes += bytes_downloaded
        stats.upload_bytes += bytes_uploaded
        stats.request_count += 1
        
        session.add(stats)
        
        if node_id is not None:
            node = session.get(ProxyNode, node_id)
            if node:
                node.download_bytes += bytes_downloaded
                session.add(node)
                
        session.commit()

from datetime import datetime, timedelta

_recent_pulls = {}

def log_pull(image: str, tag: str, client_ip: str):
    now = datetime.now()
    
    # Clean up cache occasionally
    if len(_recent_pulls) > 1000:
        cutoff = now - timedelta(seconds=60)
        keys_to_del = [k for k, v in _recent_pulls.items() if v < cutoff]
        for k in keys_to_del:
            del _recent_pulls[k]

    cache_key_exact = f"{client_ip}_{image}_{tag}"
    cache_key_image = f"{client_ip}_{image}"
    
    # 1. Skip exact duplicate (e.g. HEAD followed by GET for the same tag within 15 seconds)
    if cache_key_exact in _recent_pulls and (now - _recent_pulls[cache_key_exact]).total_seconds() < 15:
        return
        
    # 2. Skip internal digest requests if we already logged a tag pull for this image recently
    if tag.startswith("sha256:"):
        if cache_key_image in _recent_pulls and (now - _recent_pulls[cache_key_image]).total_seconds() < 15:
            return

    # Log it
    _recent_pulls[cache_key_exact] = now
    _recent_pulls[cache_key_image] = now

    with Session(engine) as session:
        pull = PullHistory(image=image, tag=tag, client_ip=client_ip)
        session.add(pull)
        session.commit()

def get_pull_history(limit: int = 100):
    with Session(engine) as session:
        return session.exec(select(PullHistory).order_by(PullHistory.request_time.desc()).limit(limit)).all()

def get_total_pull_count():
    with Session(engine) as session:
        return session.exec(select(func.count(PullHistory.id))).one()

def get_traffic_stats():
    with Session(engine) as session:
        return session.exec(select(TrafficStats).order_by(TrafficStats.date.desc()).limit(30)).all()
