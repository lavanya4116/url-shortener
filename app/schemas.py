from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

# What the user sends to create a short URL
class URLCreate(BaseModel):
    original_url: HttpUrl
    expires_in_days: Optional[int] = None  # None = never expires

# What we return to the user
class URLResponse(BaseModel):
    short_code: str
    original_url: str
    short_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True