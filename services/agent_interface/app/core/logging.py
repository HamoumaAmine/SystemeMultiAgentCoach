import logging
import time
from fastapi import Request

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

async def log_requests_middleware(request: Request, call_next):
    logger = logging.getLogger("agent_interface")
    start = time.time()

    response = await call_next(request)

    duration = (time.time() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration:.1f} ms)"
    )
    return response
