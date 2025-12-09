from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
import httpx
from app.services import proxy_manager, traffic_logger
import logging
from urllib.parse import urlparse, quote, unquote
import base64
import re

router = APIRouter()
logger = logging.getLogger("docker_proxy")

# Standard Docker Hub Auth URL (Fallback)
DOCKER_AUTH_URL = "https://auth.docker.io/token"

async def stream_response(response: httpx.Response):
    async for chunk in response.aiter_bytes():
        traffic_logger.log_traffic(bytes_downloaded=len(chunk))
        yield chunk

@router.get("/token")
async def proxy_token(request: Request):
    """
    Proxy the auth token request to the correct upstream Auth Server.
    The upstream realm should be passed in the '_upstream_realm' query param (base64 encoded),
    which was injected by our /v2/ handler during the 401 challenge.
    """
    upstream_realm_b64 = request.query_params.get("_upstream_realm")
    url = DOCKER_AUTH_URL
    
    if upstream_realm_b64:
        try:
            # Reverse the encoding: unquote -> urlsafe_b64decode -> decode utf-8
            decoded_b64 = unquote(upstream_realm_b64)
            # Fix padding if missing (urlsafe_b64decode is strict about padding in some versions?)
            # Usually strict padding is required.
            missing_padding = len(decoded_b64) % 4
            if missing_padding:
                decoded_b64 += '=' * (4 - missing_padding)
            
            url = base64.urlsafe_b64decode(decoded_b64).decode('utf-8')
            logger.info(f"Resolved upstream token URL: {url}")
        except Exception as e:
            logger.warning(f"Failed to decode _upstream_realm: {e}, falling back to default.")
            
    # Forward all other query params to the upstream auth server
    # We must exclude _upstream_realm from the forwarded params
    params = dict(request.query_params)
    params.pop("_upstream_realm", None)
    
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers)
            
            # Log upload traffic (minimal for token)
            traffic_logger.log_traffic(bytes_uploaded=len(str(request.query_params)))

            resp_headers = dict(resp.headers)
            resp_headers.pop("content-length", None)
            resp_headers.pop("content-encoding", None)

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers
            )
    except Exception as e:
        logger.error(f"Token proxy error for {url}: {e}")
        return Response(content=f"Auth Error: {e}", status_code=500)


async def parse_www_authenticate(header: str):
    """Parse Www-Authenticate header to extract realm, service, and scope."""
    info = {}
    for key in ["realm", "service", "scope"]:
        match = re.search(f'{key}="([^"]+)"', header)
        if match:
            info[key] = match.group(1)
    return info

async def get_upstream_token(realm: str, service: str, scope: str, username: str = None, password: str = None) -> str:
    """Fetch Bearer token from upstream realm using provided credentials (or anonymously)."""
    params = {}
    if service:
        params["service"] = service
    if scope:
        params["scope"] = scope
    
    try:
        if username and password:
            logger.info(f"Fetching token from {realm} for user {username} scope={scope}")
            auth_kwargs = {"auth": (username, password)}
        else:
            logger.info(f"Fetching anonymous token from {realm} scope={scope}")
            auth_kwargs = {}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(realm, params=params, **auth_kwargs)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("token") or data.get("access_token")
            else:
                logger.error(f"Failed to get token from {realm}: {resp.status_code} - {resp.text}")
                return None
    except Exception as e:
        logger.error(f"Token fetch error: {e}")
        return None

async def proxy_v2(path: str, request: Request):
    # 1. Get Best Proxy Node (and adjusted path if prefix matched)
    proxy_node, adjusted_path = proxy_manager.get_best_proxy(path)
    upstream_base = proxy_node.url
    
    # Ensure no trailing slash on base, lead slash on path handled by f-string logic
    upstream_url = f"{upstream_base.rstrip('/')}/v2/{adjusted_path}"
    
    # Query params
    if request.url.query:
        upstream_url += f"?{request.url.query}"
    
    # Headers
    # Use items() to preserve multi-value headers (e.g., Accept)
    headers_list = []
    for key, value in request.headers.items():
        if key.lower() not in ["host", "content-length"]:
            headers_list.append((key, value))
    
    # Body
    content = await request.body()
    traffic_logger.log_traffic(bytes_uploaded=len(content))

    client = httpx.AsyncClient(follow_redirects=True, timeout=None)
    
    async def send_request(url, head, body, auth=None):
        req = client.build_request(
            request.method,
            url,
            headers=head,
            content=body
        )
        if auth: 
             req.headers["Authorization"] = auth
             
        return await client.send(req, stream=True)

    r = None
    try:
        # First attempt (Transparency / or client's own Auth)
        r = await send_request(upstream_url, headers_list, content)
        
        # Check for 401 and if we can attempt auto-auth (either with stored creds OR anonymous)
        if r.status_code == 401:
            auth_header = r.headers.get("www-authenticate")
            if auth_header and "Bearer" in auth_header:
                # Close previous stream
                await r.aclose()
                
                logger.info(f"Upstream 401 (Bearer), attempting auto-auth for {proxy_node.name}")
                auth_info = await parse_www_authenticate(auth_header)
                if auth_info.get("realm"):
                    token = await get_upstream_token(
                        auth_info["realm"], 
                        auth_info.get("service"), 
                        auth_info.get("scope"),
                        proxy_node.username,
                        proxy_node.password
                    )
                    
                    if token:
                        logger.info("Got upstream token, retrying request...")
                        # Copy headers list
                        retry_headers = list(headers_list)
                        retry_headers.append(("Authorization", f"Bearer {token}"))
                        r = await send_request(upstream_url, retry_headers, content)
                    else:
                        logger.warning("Failed to obtain upstream token, returning original 401.")
                        # Re-open the original request or let it fall through? 
                        # We need to re-request to get the 401 body/headers back if we closed it.
                        r = await send_request(upstream_url, headers_list, content)
            
            elif auth_header and "Basic" in auth_header and proxy_node.username and proxy_node.password:
                # Close previous stream
                await r.aclose()
                logger.info(f"Upstream 401 (Basic), attempting auto-auth for {proxy_node.name}")
                
                retry_headers = list(headers_list)
                # Manual Basic Auth Header Construction
                auth_str = f"{proxy_node.username}:{proxy_node.password}"
                b64_auth = base64.b64encode(auth_str.encode()).decode()
                retry_headers.append(("Authorization", f"Basic {b64_auth}"))
                
                logger.info("Retrying request with Basic Auth...")
                r = await send_request(upstream_url, retry_headers, content)

    except Exception as e:
        if r: await r.aclose()
        await client.aclose()
        logger.error(f"Connection error: {e}")
        return Response(content=str(e), status_code=502)

    # Process Headers
    resp_headers = dict(r.headers)
    
    # Www-Authenticate Rewrite logic
    auth_header = resp_headers.get("www-authenticate")
    if auth_header:
        logger.info(f"Original Www-Authenticate: {auth_header}")
        my_host = f"{request.url.scheme}://{request.url.netloc}"
        import re
        realm_pattern = re.compile(r'realm="([^"]+)"')
        match = realm_pattern.search(auth_header)
        if match:
            upstream_realm = match.group(1)
            # Encode upstream realm to pass to our token endpoint
            # Use urlsafe_b64encode to avoid +/ and quote to handle padding =
            b64_realm = base64.urlsafe_b64encode(upstream_realm.encode()).decode()
            
            # Construct new realm URL: https://my-proxy/token?_upstream_realm=...
            # We also quote just in case, though urlsafe usually only has -_ and =
            new_realm = f"{my_host}/token?_upstream_realm={quote(b64_realm)}"
            
            # Replace in header
            resp_headers["www-authenticate"] = auth_header.replace(upstream_realm, new_realm)
            logger.info(f"Rewritten Www-Authenticate: {resp_headers['www-authenticate']}")
    
    # Exclude headers
    if request.method != "HEAD":
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
    # Log Docker Pulls (Manifest Requests)
    if request.method == "GET" and "/manifests/" in path:
        try:
            # Pattern: name/manifests/reference
            match = re.match(r"^(.+)/manifests/(.+)$", path)
            if match:
                image = match.group(1)
                tag = match.group(2)
                client_ip = request.client.host if request.client else "unknown"
                traffic_logger.log_pull(image=image, tag=tag, client_ip=client_ip)
                logger.info(f"Logged pull: {image}:{tag} from {client_ip}")
        except Exception as e:
            logger.error(f"Failed to log pull: {e}")
            
    return await proxy_v2(path=path, request=request)


