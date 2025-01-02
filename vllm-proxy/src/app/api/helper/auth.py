import os

from fastapi import Header, HTTPException

TOKEN = os.getenv("TOKEN")

# Dependency to verify the Authorization header
def verify_authorization_header(authorization: str = Header("Authorization")):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Invalid or missing Authorization header"
        )
    token = authorization.split("Bearer ")[1]
    if token != TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token
