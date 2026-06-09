from pydantic import BaseModel


class ClubResponse(BaseModel):
    id: int
    name: str
