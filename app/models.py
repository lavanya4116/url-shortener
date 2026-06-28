from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String(10), unique=True, index=True, nullable=False)
    click_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)


class ClickEvent(Base):
    """
    Stores individual click events for detailed analytics.
    Separate table so URL table stays lean.
    This is the 'wide table vs narrow table' design pattern.
    """
    __tablename__ = "click_events"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String(10), index=True, nullable=False)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now())
    # Optional enrichment — add more later
    user_agent = Column(String, nullable=True)
    referer = Column(String, nullable=True)