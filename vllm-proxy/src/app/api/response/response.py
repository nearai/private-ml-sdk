def ok(data: dict = None):
    return data or dict()


def error(message: str = "error", type: str = "error_type", param: str = None, code: str = None):
    return dict(
        error=dict(
            message=message,
            type=type,
            param=param,
            code=code,
        )
    )

def unexpect_error():
    return error(
        message="An unexpected error occurred.",
        type="unknown_error",
        param=None,
        code=None,
    )
