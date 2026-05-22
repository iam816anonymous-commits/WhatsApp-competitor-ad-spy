from datetime import datetime, UTC
from typing import List, Optional
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class ScrapeRun(Base):
    __tablename__ = 'scrape_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    status: Mapped[str] = mapped_column(String) # PENDING, RUNNING, COMPLETED, FAILED
    analysis_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # Phase 2 Intelligence Fields
    cta_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    emotion: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    offer_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price_point: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    discount: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    urgency_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    visual_style: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    headline: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hook_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cta_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    brand_color: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="run", cascade="all, delete-orphan")

class ScrapeSchedule(Base):
    __tablename__ = 'scrape_schedules'
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String)
    frequency_hours: Mapped[int] = mapped_column()
    next_run_at: Mapped[datetime] = mapped_column()
    is_active: Mapped[int] = mapped_column(default=1)

class ExtractedAd(Base):
    __tablename__ = 'extracted_ads'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('scrape_runs.id'))
    ad_text: Mapped[str] = mapped_column(Text)
    launch_date: Mapped[str] = mapped_column(String)
    media_links: Mapped[str] = mapped_column(Text)
    local_media_path: Mapped[Optional[str]] = mapped_column(nullable=True)
    content_hash: Mapped[str] = mapped_column(unique=True)
    final_destination_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    funnel_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    # Phase 3 Visual Intelligence
    creative_embedding: Mapped[Optional[bytes]] = mapped_column(nullable=True)

    run: Mapped["ScrapeRun"] = relationship("ScrapeRun", back_populates="ads")
