from datetime import date
from sqlmodel import Session, select
from app.database import engine
from app.models import TrafficStats

def log_traffic(bytes_downloaded: int = 0, bytes_uploaded: int = 0):
    today_str = date.today().isoformat()
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

def get_traffic_stats():
    with Session(engine) as session:
        return session.exec(select(TrafficStats).order_by(TrafficStats.date.desc()).limit(30)).all()
