import asyncio
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.cache import get_all_pending_clicks, reset_click_count, delete_cached_url


async def flush_click_counts():
    """
    Background task — runs every 60 seconds.
    Reads buffered clicks from Redis and writes to PostgreSQL in batch.
    
    Why batch writes?
    - 1M redirects = 1M DB writes (bad) vs 1 batch write (good)
    - PostgreSQL handles batch updates much more efficiently
    - Redis INCR is atomic so no clicks are lost
    """
    while True:
        await asyncio.sleep(60)     # flush every 60 seconds
        await _do_flush()


async def _do_flush():
    """Do the actual flush — separated so we can call it manually in tests"""
    pending = get_all_pending_clicks()

    if not pending:
        return      # nothing to flush

    db: Session = SessionLocal()
    try:
        flushed = 0
        for short_code, count in pending.items():

            # Batch update — one query per URL
            updated = db.query(models.URL).filter(
                models.URL.short_code == short_code
            ).update(
                {"click_count": models.URL.click_count + count}
            )

            if updated:
                # Only reset Redis counter if DB update succeeded
                reset_click_count(short_code)
                flushed += 1

        db.commit()
        print(
            f"[tasks] Flushed {flushed} URL click counts "
            f"({sum(pending.values())} total clicks)"
        )

    except Exception as e:
        db.rollback()
        print(f"[tasks] Flush failed: {e}")
        # Don't reset Redis — counts preserved for next flush attempt
    finally:
        db.close()


async def cleanup_expired_urls():
    """
    Background task — runs every hour.
    Soft-deletes expired URLs so they don't clutter the DB.
    
    Why soft delete?
    We keep the row for analytics — just set is_active = False.
    Analytics data (click_events) stays intact.
    """
    while True:
        await asyncio.sleep(3600)   # every hour
        await _do_cleanup()


async def _do_cleanup():
    from datetime import datetime, timezone
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)

        expired = db.query(models.URL).filter(
            models.URL.expires_at <= now,
            models.URL.is_active == True
        ).all()

        if not expired:
            db.close()
            return

        for url in expired:
            url.is_active = False
            # Also remove from Redis cache — without this, an expired URL that's
            # still cached would keep redirecting for up to CACHE_TTL (1hr) since
            # the redirect endpoint trusts a cache hit without re-checking is_active/expiry.
            delete_cached_url(url.short_code)
            reset_click_count(url.short_code)

        db.commit()
        print(f"[tasks] Cleaned up {len(expired)} expired URLs")

    except Exception as e:
        db.rollback()
        print(f"[tasks] Cleanup failed: {e}")
    finally:
        db.close()