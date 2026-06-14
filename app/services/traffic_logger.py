from datetime import date
from sqlmodel import Session, select, func
from app.database import engine
from app.models import TrafficStats, PullHistory, get_shanghai_time

def log_traffic(bytes_downloaded: int = 0, bytes_uploaded: int = 0):
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
        session.commit()

def log_pull(image: str, tag: str, client_ip: str):
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
