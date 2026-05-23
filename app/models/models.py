from datetime import datetime, UTC
from typing import List, Optional
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey, JSON, Float, MetaData
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column

# Naming convention for SQLite migrations
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)

class Organization(Base):
    __tablename__ = 'organizations'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    monthly_budget: Mapped[float] = mapped_column(Float, default=100.0)

    users: Mapped[List["User"]] = relationship("User", back_populates="org")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="org")

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    email: Mapped[str] = mapped_column(String, unique=True)
    role: Mapped[str] = mapped_column(String, default="analyst")

    org: Mapped["Organization"] = relationship("Organization", back_populates="users")

class Project(Base):
    __tablename__ = 'projects'
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    name: Mapped[str] = mapped_column(String)

    org: Mapped["Organization"] = relationship("Organization", back_populates="projects")
    schedules: Mapped[List["ScrapeSchedule"]] = relationship("ScrapeSchedule", back_populates="project")

class OrganizationUsage(Base):
    __tablename__ = 'organization_usage'
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    month: Mapped[str] = mapped_column(String) # e.g. "2023-10"
    total_spend: Mapped[float] = mapped_column(Float, default=0.0)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[Optional[int]] = mapped_column(ForeignKey('organizations.id'), nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

class CompetitorProfile(Base):
    __tablename__ = 'competitor_profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_name: Mapped[str] = mapped_column(String, unique=True)
    first_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    last_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    offer_shift_count: Mapped[int] = mapped_column(default=0)
    creative_count: Mapped[int] = mapped_column(default=0)
    winning_assets: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON or list
    dominant_hook: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    market_velocity: Mapped[float] = mapped_column(default=0.0)

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
    personas: Mapped[List["Persona"]] = relationship("Persona", back_populates="brand")
    hooks: Mapped[List["Hook"]] = relationship("Hook", back_populates="brand")
    events: Mapped[List["MarketEvent"]] = relationship("MarketEvent", back_populates="brand")

class Persona(Base):
    __tablename__ = 'personas'
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey('brands.id'))
    name: Mapped[str] = mapped_column(String) # e.g. "Fitness Enthusiast"
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="personas")
    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="persona_rel")

class Hook(Base):
    __tablename__ = 'hooks'
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey('brands.id'))
    text: Mapped[str] = mapped_column(Text)
    type: Mapped[Optional[str]] = mapped_column(String, nullable=True) # e.g. "Question", "Stat"
    survival_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    brand: Mapped["Brand"] = relationship("Brand", back_populates="hooks")
    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="hook_rel")

class MarketEvent(Base):
    __tablename__ = 'market_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey('brands.id'))
    event_type: Mapped[str] = mapped_column(String) # e.g. "Offer Shift", "Price Change"
    description: Mapped[str] = mapped_column(Text)
    old_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    brand: Mapped["Brand"] = relationship("Brand", back_populates="events")

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

    # Phase 5 additions
    pricing: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email_capture_detected: Mapped[bool] = mapped_column(default=False)
    has_checkout: Mapped[bool] = mapped_column(default=False)

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

class CritiqueEvent(Base):
    __tablename__ = 'critique_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('scrape_runs.id'))
    ad_id: Mapped[Optional[int]] = mapped_column(ForeignKey('extracted_ads.id'), nullable=True)
    issue_type: Mapped[str] = mapped_column(String) # e.g. "hallucination", "low_confidence"
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[float] = mapped_column(default=0.5)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

class EmbeddingCache(Base):
    __tablename__ = 'embedding_cache'
    content_hash: Mapped[str] = mapped_column(String, primary_key=True)
    vector: Mapped[bytes] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

class RawEvidence(Base):
    __tablename__ = 'raw_evidence'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('scrape_runs.id'))
    ad_id: Mapped[Optional[int]] = mapped_column(ForeignKey('extracted_ads.id'), nullable=True)
    evidence_type: Mapped[str] = mapped_column(String) # "html", "screenshot", "raw_ai_json"
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    run: Mapped["ScrapeRun"] = relationship("ScrapeRun", back_populates="evidence")

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

    # Validation & Critique
    critique_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hallucination_flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    ads: Mapped[List["ExtractedAd"]] = relationship("ExtractedAd", back_populates="run", cascade="all, delete-orphan")
    evidence: Mapped[List["RawEvidence"]] = relationship("RawEvidence", back_populates="run", cascade="all, delete-orphan")

class ScrapeSchedule(Base):
    __tablename__ = 'scrape_schedules'
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey('projects.id'), nullable=True)
    query: Mapped[str] = mapped_column(String)
    frequency_hours: Mapped[int] = mapped_column()
    next_run_at: Mapped[datetime] = mapped_column()
    is_active: Mapped[int] = mapped_column(default=1)

    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="schedules")

class ExtractedAd(Base):
    __tablename__ = 'extracted_ads'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('scrape_runs.id'))
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey('brands.id'), nullable=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey('campaigns.id'), nullable=True)
    offer_id: Mapped[Optional[int]] = mapped_column(ForeignKey('offers.id'), nullable=True)
    landing_page_id: Mapped[Optional[int]] = mapped_column(ForeignKey('landing_pages.id'), nullable=True)
    cluster_id: Mapped[Optional[int]] = mapped_column(ForeignKey('creative_clusters.id'), nullable=True)
    persona_id: Mapped[Optional[int]] = mapped_column(ForeignKey('personas.id'), nullable=True)
    hook_id: Mapped[Optional[int]] = mapped_column(ForeignKey('hooks.id'), nullable=True)

    ad_text: Mapped[str] = mapped_column(Text)
    headline: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    launch_date: Mapped[str] = mapped_column(String)
    media_links: Mapped[str] = mapped_column(Text)
    local_media_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_hash: Mapped[str] = mapped_column(unique=True)
    final_destination_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    funnel_type: Mapped[Optional[str]] = mapped_column(nullable=True)
    last_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    # Predictive Metrics
    winner_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fatigue_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Phase 3/5 Visual Intelligence
    creative_embedding: Mapped[Optional[bytes]] = mapped_column(nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(default=False)
    repair_attempts: Mapped[int] = mapped_column(default=0)
    phash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    dominant_colors: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    run: Mapped["ScrapeRun"] = relationship("ScrapeRun", back_populates="ads")
    brand: Mapped[Optional["Brand"]] = relationship("Brand", back_populates="ads")
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="ads")
    offer: Mapped[Optional["Offer"]] = relationship("Offer", back_populates="ads")
    landing_page: Mapped[Optional["LandingPage"]] = relationship("LandingPage", back_populates="ads")
    cluster: Mapped[Optional["CreativeCluster"]] = relationship("CreativeCluster", back_populates="ads")
    persona_rel: Mapped[Optional["Persona"]] = relationship("Persona", back_populates="ads")
    hook_rel: Mapped[Optional["Hook"]] = relationship("Hook", back_populates="ads")
