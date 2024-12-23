import uvicorn

from app.logger import LOGGING_CONFIG

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_config=LOGGING_CONFIG,
        log_level="info",
    )
