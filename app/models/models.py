from datetime import datetime, UTC
from typing import List, Optional
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey, JSON, Float
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Brand(Base):
    __tablename__ = 'brands'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    industry: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_monitored: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="brand")
    campaigns: Mapped[List["Campaign"]] = relationship("Campaign", back_populates="brand")
    offers: Mapped[List["Offer"]] = relationship("Offer", back_populates="brand")
    snapshots: Mapped[List["TrendSnapshot"]] = relationship("TrendSnapshot", back_populates="brand")

class Campaign(Base):
    __tablename__ = 'campaigns'
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey('brands.id'))
    name: Mapped[str] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="campaigns")
    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="campaign")

class Offer(Base):
    __tablename__ = 'offers'
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey('brands.id'))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price_point: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    discount: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[int] = mapped_column(Integer, default=1)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="offers")
    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="offer")

class LandingPage(Base):
    __tablename__ = 'landing_pages'
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String, unique=True)
    resolved_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    headline: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cta_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pixels_detected: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    funnel_stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="landing_page")

class CreativeCluster(Base):
    __tablename__ = 'creative_clusters'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    centroid_embedding: Mapped[Optional[bytes]] = mapped_column(nullable=True)

    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="cluster")

class TrendSnapshot(Base):
    __tablename__ = 'trend_snapshots'
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey('brands.id'))
    date: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    ad_count: Mapped[int] = mapped_column(Integer, default=0)
    new_ads_count: Mapped[int] = mapped_column(Integer, default=0)
    dominant_emotion: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="snapshots")

class ScrapeRun(Base):
    __tablename__ = 'scrape_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    status: Mapped[str] = mapped_column(String) # PENDING, RUNNING, COMPLETED, FAILED
    analysis_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    # AI Summary Fields
    cta_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    emotion: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    offer_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    urgency_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    persona: Mapped[Optional[str]] = mapped_column(String, nullable=True)

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
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey('brands.id'), nullable=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey('campaigns.id'), nullable=True)
    offer_id: Mapped[Optional[int]] = mapped_column(ForeignKey('offers.id'), nullable=True)
    landing_page_id: Mapped[Optional[int]] = mapped_column(ForeignKey('landing_pages.id'), nullable=True)
    cluster_id: Mapped[Optional[int]] = mapped_column(ForeignKey('creative_clusters.id'), nullable=True)

    ad_text: Mapped[str] = mapped_column(Text)
    headline: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    launch_date: Mapped[str] = mapped_column(String)
    media_links: Mapped[str] = mapped_column(Text)
    local_media_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_hash: Mapped[str] = mapped_column(unique=True)
    final_destination_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    funnel_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    # Phase 3 Visual Intelligence
    creative_embedding: Mapped[Optional[bytes]] = mapped_column(nullable=True)

    run: Mapped["ScrapeRun"] = relationship("ScrapeRun", back_populates="ads")
    brand: Mapped[Optional["Brand"]] = relationship("Brand", back_populates="ads")
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="ads")
    offer: Mapped[Optional["Offer"]] = relationship("Offer", back_populates="ads")
    landing_page: Mapped[Optional["LandingPage"]] = relationship("LandingPage", back_populates="ads")
    cluster: Mapped[Optional["CreativeCluster"]] = relationship("CreativeCluster", back_populates="ads")
