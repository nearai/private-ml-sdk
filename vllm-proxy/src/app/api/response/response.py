from fastapi.responses import JSONResponse


def ok(data: dict = None):
    return data or dict()


def error(
    status_code: int,
    message: str = "error",
    type: str = "error_type",
    param: str = None,
    code: str = None,
):
    content = dict(
        error=dict(
            message=message,
            type=type,
            param=param,
            code=code,
        )
    )
    return JSONResponse(status_code=status_code, content=content)


def unexpect_error():
    return error(
        status_code=500,
        message="An unexpected error occurred.",
        type="unknown_error",
        param=None,
        code=None,
    )


def invalid_signing_algo():
    return error(
        status_code=400,
        message="Invalid signing algorithm. Must be 'ed25519' or 'ecdsa'",
        type="invalid_signing_algo",
        param=None,
        code=None,
    )


def http_exception(status_code: int, message: str):
    return error(status_code=status_code, message=message, type="http_exception")


def not_found(message: str):
    return error(status_code=404, message=message, type="not_found")