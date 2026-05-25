from pydantic import BaseModel


class AuthorizeResponse(BaseModel):
    authorization_url: str
