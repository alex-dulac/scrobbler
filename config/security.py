from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette import status

from config import settings


class CustomHTTPBearer(HTTPBearer):
    """
   Custom HTTP Bearer authentication class.

   This class extends the HTTPBearer class to provide custom behavior for handling
   HTTP Bearer authentication. It overrides the __call__ method to handle the
   extraction and validation of the authorization credentials from the request.

   Parameters:
   request (Request): The incoming HTTP request.

   Returns:
   HTTPAuthorizationCredentials: The extracted authorization credentials if present.

   Raises:
   HTTPException: If no authorization credentials are provided, an HTTPException
       is raised with a 401 status code and a message indicating the issue.
   """
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        try:
            credentials: HTTPAuthorizationCredentials = await super().__call__(request)
            if credentials:
                return credentials
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No authorization provided",
                headers={"WWW-Authenticate": "Bearer"},
            )


http_scheme = CustomHTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(http_scheme)):
    token = credentials.credentials

    if token != settings.APP_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
