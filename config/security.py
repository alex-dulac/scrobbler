from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status

from config import settings

http_scheme = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(http_scheme)):
    """
    Verifies the provided token against the application's token.

    Parameters:
    credentials (HTTPAuthorizationCredentials): The token provided by the client.
        This is obtained from the HTTP Bearer scheme and is automatically injected by FastAPI.

    Returns:
    None: If the token is valid, the function does not return anything.

    Raises:
    HTTPException: If the token is invalid or expired, an HTTPException is raised with
        a 401 status code and a message indicating the issue.

    """
    token = credentials.credentials

    if token != settings.APP_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
