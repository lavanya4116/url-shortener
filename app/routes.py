from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app import models
from app.schemas import URLCreate, URLResponse
from app.utils import encode_base62
import os

router = APIRouter()

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


@router.post("/shorten", response_model=URLResponse)
def shorten_url(payload: URLCreate, db: Session = Depends(get_db)):
    
    # Calculate expiry if user gave expires_in_days
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)

    # Step 1: Save to DB first to get the auto-increment ID
    db_url = models.URL(
        original_url=str(payload.original_url),
        short_code="temp",          # placeholder, we update after
        expires_at=expires_at
    )
    db.add(db_url)
    db.flush()                      # flush to get the ID without full commit

    # Step 2: Generate Base62 short code from the ID
    short_code = encode_base62(db_url.id)

    # Step 3: Update the row with real short code
    db_url.short_code = short_code
    db.commit()
    db.refresh(db_url)

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

    # Look up the short code
    db_url = db.query(models.URL).filter(
        models.URL.short_code == short_code,
        models.URL.is_active == True
    ).first()

    # 404 if not found
    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Check expiry
    if db_url.expires_at and datetime.now(timezone.utc) > db_url.expires_at:
        raise HTTPException(status_code=410, detail="This link has expired")

    # Increment click count
    db_url.click_count += 1
    db.commit()

    # 301 redirect to original URL
    return RedirectResponse(url=db_url.original_url, status_code=301)


@router.get("/info/{short_code}", response_model=URLResponse)
def get_url_info(short_code: str, db: Session = Depends(get_db)):
    """Get analytics info about a short URL without redirecting"""
    
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
    """Soft delete — deactivates the URL without removing from DB"""
    
    db_url = db.query(models.URL).filter(
        models.URL.short_code == short_code
    ).first()

    if not db_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    db_url.is_active = False
    db.commit()

    return {"message": f"URL {short_code} has been deactivated"}