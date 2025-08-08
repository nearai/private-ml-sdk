from fastapi import FastAPI, HTTPException, Request

from .api import router as api_router
from .api.response.response import ok, unexpect_error, http_exception
from .logger import log

app = FastAPI()
app.include_router(api_router)


@app.get("/")
async def root():
    return ok()


# Custom global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all uncaught exceptions globally.
    """
    # handle HTTPException
    if isinstance(exc, HTTPException):
        log.error(f"HTTPException: {exc.detail}")
        return http_exception(exc.status_code, exc.detail)

    log.error(f"Unhandled exception: {exc}")
    return unexpect_error()
