from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import settings


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.APP_TOKEN)


def verify_token(token: str = Depends(oauth2_scheme)):
    pass
