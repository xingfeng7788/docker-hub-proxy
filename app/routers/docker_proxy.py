from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
import httpx
from app.services import proxy_manager, traffic_logger
import logging
from urllib.parse import urlparse

router = APIRouter()
logger = logging.getLogger("docker_proxy")

# Standard Docker Hub Auth URL
DOCKER_AUTH_URL = "https://auth.docker.io/token"

async def stream_response(response: httpx.Response):
    async for chunk in response.aiter_bytes():
        traffic_logger.log_traffic(bytes_downloaded=len(chunk))
        yield chunk

@router.get("/token")
async def proxy_token(request: Request):
    """
    Proxy the auth token request to Docker Hub Auth.
    """
    # Construct upstream URL
    url = DOCKER_AUTH_URL
    if request.url.query:
        url += f"?{request.url.query}"

    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            
            # Log upload traffic (minimal for token)
            traffic_logger.log_traffic(bytes_uploaded=len(request.url.query)) # Rough approx

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=dict(resp.headers)
            )
    except Exception as e:
        logger.error(f"Token proxy error: {e}")
        return Response(content="Auth Error", status_code=500)

async def proxy_v2(path: str, request: Request):
    # 1. Get Best Proxy
    upstream_base = proxy_manager.get_best_proxy()
    
    # Ensure no trailing slash on base, lead slash on path handled by f-string logic
    upstream_url = f"{upstream_base.rstrip('/')}/v2/{path}"
    
    # Query params
    if request.url.query:
        upstream_url += f"?{request.url.query}"
    
    # Headers
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # Body
    content = await request.body()
    
    # Log upload
    traffic_logger.log_traffic(bytes_uploaded=len(content))

    client = httpx.AsyncClient(follow_redirects=True, timeout=None) # No timeout for large downloads
    try:
        req = client.build_request(
            request.method,
            upstream_url,
            headers=headers,
            content=content
        )
        r = await client.send(req, stream=True)
    except Exception as e:
        await client.aclose()
        logger.error(f"Connection error: {e}")
        return Response(content=str(e), status_code=502)

    # Process Headers
    resp_headers = dict(r.headers)
    
    # Www-Authenticate Rewrite
    auth_header = resp_headers.get("www-authenticate")
    if auth_header:
        # Simple replace of realm
        # We want realm="https://<my-host>/token"
        my_host = f"{request.url.scheme}://{request.url.netloc}"
        
        import re
        realm_pattern = re.compile(r'realm="([^"]+)"')
        match = realm_pattern.search(auth_header)
        if match:
            upstream_realm = match.group(1)
            # Replace with our token endpoint
            new_realm = f"{my_host}/token"
            new_header = auth_header.replace(upstream_realm, new_realm)
            resp_headers["www-authenticate"] = new_header
    
    # Exclude some headers
    resp_headers.pop("content-length", None)
    resp_headers.pop("content-encoding", None)

    async def iter_response():
        try:
            async for chunk in r.aiter_bytes():
                traffic_logger.log_traffic(bytes_downloaded=len(chunk))
                yield chunk
        finally:
            await r.aclose()
            await client.aclose()

    return StreamingResponse(
        iter_response(),
        status_code=r.status_code,
        headers=resp_headers
    )

# Explicitly handle /v2/ (root) for docker login checks
@router.api_route("/v2/", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_v2_root(request: Request):
    return await proxy_v2(path="", request=request)

# Handle subpaths
@router.api_route("/v2/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_v2_path(path: str, request: Request):
    return await proxy_v2(path=path, request=request)


