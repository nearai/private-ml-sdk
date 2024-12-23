from typing import Union
from hashlib import sha256
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .api import router as api_router
from .api.response.response import ok, error, unexpect_error
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
        # return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return error(exc.detail)

    log.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content=unexpect_error())
