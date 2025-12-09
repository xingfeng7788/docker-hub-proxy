from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from app.services import traffic_logger, proxy_manager
from app.database import engine
from sqlmodel import Session, select
from app.models import TrafficStats, ProxyNode
import httpx

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    proxies = proxy_manager.get_all_proxies()
    stats = traffic_logger.get_traffic_stats()
    
    # Calculate totals
    total_download = sum(s.download_bytes for s in stats)
    total_reqs = sum(s.request_count for s in stats)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "proxies": [p.model_dump(mode='json') for p in proxies],
        "stats": [s.model_dump(mode='json') for s in stats],
        "total_download": total_download,
        "total_reqs": total_reqs
    })

@router.get("/api/search")
async def search_images(q: str):
    """Proxy search to Docker Hub"""
    url = f"https://hub.docker.com/v2/search/repositories/?query={q}"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            return JSONResponse(content=resp.json())
        except Exception as e:
            return JSONResponse(content={"results": []}, status_code=500)

@router.post("/api/proxies")
async def add_proxy_node(
    name: str = Form(...), 
    url: str = Form(...),
    username: str = Form(None),
    password: str = Form(None)
):
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    proxy_manager.add_proxy(name, url, username, password)
    return {"status": "ok"}

@router.put("/api/proxies/{proxy_id}")
async def update_proxy_node(
    proxy_id: int,
    name: str = Form(...),
    url: str = Form(...),
    username: str = Form(None),
    password: str = Form(None)
):
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    node = proxy_manager.update_proxy(proxy_id, name, url, username, password)
    if not node:
        raise HTTPException(status_code=404, detail="Proxy not found")
        
    return {"status": "ok"}

@router.delete("/api/proxies/{proxy_id}")
async def delete_proxy_node(proxy_id: int):
    proxy_manager.delete_proxy(proxy_id)
    return {"status": "ok"}

@router.post("/api/test-speed")
async def trigger_speed_test():
    await proxy_manager.run_speed_test()
    return {"status": "started"}
