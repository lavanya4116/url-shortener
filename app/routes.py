from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app import models
from app.schemas import URLCreate, URLResponse, URLAnalyticsResponse, ClickEventResponse, DailyBreakdown
from app.utils import encode_base62
from app.cache import get_cached_url, set_cached_url, delete_cached_url
from app.rate_limiter import rate_limit_dependency
import os
from app.models import ClickEvent
from app.cache import (
    get_cached_url,
    set_cached_url,
    delete_cached_url,
    increment_click_redis,
    get_redis_click_count
)

router = APIRouter()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


@router.post(
    "/shorten",
    response_model=URLResponse,
    dependencies=[Depends(rate_limit_dependency("shorten"))]   # ✅ protected
)
def shorten_url(payload: URLCreate, db: Session = Depends(get_db)):
    
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

    db_url = models.URL(
        original_url=str(payload.original_url),
        short_code="temp",
        expires_at=expires_at
    )
    db.add(db_url)
    db.flush()

    short_code = encode_base62(db_url.id)
    db_url.short_code = short_code
    db.commit()
    db.refresh(db_url)

    set_cached_url(short_code, db_url.original_url)

    return URLResponse(
        short_code=db_url.short_code,
        original_url=db_url.original_url,
        short_url=f"{BASE_URL}/{db_url.short_code}",
        click_count=db_url.click_count,
        created_at=db_url.created_at,
        expires_at=db_url.expires_at
    )
@router.get("/info/{short_code}", response_model=URLResponse)
def get_url_info(short_code: str, db: Session = Depends(get_db)):

    db_url = db.query(models.URL).filter(
        models.URL.short_code == short_code,
        models.URL.is_active == True
    ).first()

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return URLResponse(
        short_code=db_url.short_code,
        original_url=db_url.original_url,
        short_url=f"{BASE_URL}/{db_url.short_code}",
        click_count=db_url.click_count,
        created_at=db_url.created_at,
        expires_at=db_url.expires_at
    )

@router.get(
    "/{short_code}",
    dependencies=[Depends(rate_limit_dependency("redirect"))]
)
def redirect_url(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    cached_url = get_cached_url(short_code)
    if cached_url:
        increment_click_redis(short_code)

        # Log click event with metadata
        event = ClickEvent(
            short_code=short_code,
            user_agent=request.headers.get("user-agent"),
            referer=request.headers.get("referer")
        )
        db.add(event)
        db.commit()

        return RedirectResponse(url=cached_url, status_code=302)

    db_url = db.query(models.URL).filter(
        models.URL.short_code == short_code,
        models.URL.is_active == True
    ).first()

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    if db_url.expires_at and datetime.now(timezone.utc) > db_url.expires_at:
        raise HTTPException(status_code=410, detail="This link has expired")

    set_cached_url(short_code, db_url.original_url)
    increment_click_redis(short_code)

    # Log click event
    event = ClickEvent(
        short_code=short_code,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer")
    )
    db.add(event)
    db.commit()

    return RedirectResponse(url=db_url.original_url, status_code=302)

@router.delete("/{short_code}")
def delete_url(short_code: str, db: Session = Depends(get_db)):

    db_url = db.query(models.URL).filter(
        models.URL.short_code == short_code
    ).first()

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    db_url.is_active = False
    db.commit()
    delete_cached_url(short_code)

    return {"message": f"URL {short_code} has been deactivated"}

@router.get("/analytics/{short_code}", response_model=URLAnalyticsResponse)
def get_analytics(short_code: str, db: Session = Depends(get_db)):

    db_url = db.query(models.URL).filter(
        models.URL.short_code == short_code
    ).first()

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    redis_buffer = get_redis_click_count(short_code)
    total_clicks = db_url.click_count + redis_buffer

    recent_clicks = db.query(ClickEvent).filter(
        ClickEvent.short_code == short_code
    ).order_by(
        ClickEvent.clicked_at.desc()
    ).limit(10).all()

    from sqlalchemy import func as sql_func, cast
    from sqlalchemy.types import Date

    daily_clicks = db.query(
        cast(ClickEvent.clicked_at, Date).label("date"),
        sql_func.count(ClickEvent.id).label("count")
    ).filter(
        ClickEvent.short_code == short_code
    ).group_by(
        cast(ClickEvent.clicked_at, Date)
    ).order_by(
        cast(ClickEvent.clicked_at, Date).desc()
    ).limit(7).all()

    # ✅ Return using the response model
    return URLAnalyticsResponse(
        short_code=db_url.short_code,
        original_url=db_url.original_url,
        short_url=f"{os.getenv('BASE_URL', 'http://localhost:8000')}/{short_code}",
        total_clicks=total_clicks,
        db_clicks=db_url.click_count,
        buffered_clicks=redis_buffer,
        is_active=db_url.is_active,
        created_at=db_url.created_at,
        expires_at=db_url.expires_at,
        recent_clicks=[
            ClickEventResponse(
                clicked_at=c.clicked_at,
                user_agent=c.user_agent,
                referer=c.referer
            )
            for c in recent_clicks
        ],
        daily_breakdown=[
            DailyBreakdown(
                date=str(d.date),
                clicks=d.count
            )
            for d in daily_clicks
        ]
    )