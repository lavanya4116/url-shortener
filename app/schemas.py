from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional

class URLCreate(BaseModel):
    original_url: HttpUrl
    expires_in_days: Optional[int] = None

class URLResponse(BaseModel):
    short_code: str
    original_url: str
    short_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True

# ✅ New schemas for analytics
class ClickEventResponse(BaseModel):
    clicked_at: datetime
    user_agent: Optional[str]
    referer: Optional[str]

    class Config:
        from_attributes = True

class DailyBreakdown(BaseModel):
    date: str
    clicks: int

class URLAnalyticsResponse(BaseModel):
    short_code: str
    original_url: str
    short_url: str
    total_clicks: int
    db_clicks: int
    buffered_clicks: int
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    recent_clicks: list[ClickEventResponse]
    daily_breakdown: list[DailyBreakdown]

    class Config:
        from_attributes = True