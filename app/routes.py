from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app import models
from app.schemas import URLCreate, URLResponse
from app.utils import encode_base62
from app.cache import get_cached_url, set_cached_url, delete_cached_url
import os

router = APIRouter()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


@router.post("/shorten", response_model=URLResponse)
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

    # Warm the cache immediately after creation
    set_cached_url(short_code, db_url.original_url)

    return URLResponse(
        short_code=db_url.short_code,
        original_url=db_url.original_url,
        short_url=f"{BASE_URL}/{db_url.short_code}",
        click_count=db_url.click_count,
        created_at=db_url.created_at,
        expires_at=db_url.expires_at
    )


@router.get("/{short_code}")
def redirect_url(short_code: str, db: Session = Depends(get_db)):

    # ✅ Step 1: Check Redis first (cache hit)
    cached_url = get_cached_url(short_code)
    if cached_url:
        # Still increment click count in DB (async would be better, fine for now)
        db_url = db.query(models.URL).filter(
            models.URL.short_code == short_code
        ).first()
        if db_url:
            db_url.click_count += 1
            db.commit()
        return RedirectResponse(url=cached_url, status_code=302)

    # ✅ Step 2: Cache miss — go to PostgreSQL
    db_url = db.query(models.URL).filter(
        models.URL.short_code == short_code,
        models.URL.is_active == True
    ).first()

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    if db_url.expires_at and datetime.now(timezone.utc) > db_url.expires_at:
        raise HTTPException(status_code=410, detail="This link has expired")

    # ✅ Step 3: Store in Redis for next time (cache population)
    set_cached_url(short_code, db_url.original_url)

    # Increment click count
    db_url.click_count += 1
    db.commit()

    return RedirectResponse(url=db_url.original_url, status_code=302)


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


@router.delete("/{short_code}")
def delete_url(short_code: str, db: Session = Depends(get_db)):

    db_url = db.query(models.URL).filter(
        models.URL.short_code == short_code
    ).first()

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    db_url.is_active = False
    db.commit()

    # ✅ Remove from cache too — stale cache = wrong redirects
    delete_cached_url(short_code)

    return {"message": f"URL {short_code} has been deactivated"}