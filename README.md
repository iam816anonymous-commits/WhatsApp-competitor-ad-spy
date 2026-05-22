# 🕵️ AdSpy Intelligence Platform (v3.0 Orchestrated)

A sophisticated Market Intelligence Platform featuring multi-agent orchestration, temporal analytics, and visual clone detection.

## 🚀 Enterprise Tier Upgrades

### 🏗️ Multi-Agent Orchestration
AdSpy now uses a formal execution graph managed by the `IntelligenceOrchestrator`:
1.  **Collector**: Async scraping of ad libraries.
2.  **Normalizer**: Entity mapping for Brands, Offers, and Landing Pages.
3.  **Vision Agent**: CLIP-based visual embedding generation.
4.  **Strategy Agent**: Deep tactical extraction using Gemini 2.0 Flash.
5.  **Market Agent**: Temporal trend analysis and volume tracking.
6.  **Alert Engine**: Automated high-signal notifications (WhatsApp/System).

### 🧠 Intelligence Memory Layer
Enhanced data models now track high-level entities:
- **Brands**: Monitor competitor aggression and website changes.
- **Campaigns**: Automatically group ads into temporal clusters.
- **Offers**: Detect price shifts and discount strategies.
- **Landing Pages**: Deep crawl extraction (Headlines, CTAs, Pixels).
- **Trend Snapshots**: Daily volume and emotion shift tracking.

### 🌐 API-First Architecture
Exposed a robust **FastAPI backend** on port `8000`:
- `POST /scrape`: Programmatic trigger for new intelligence jobs.
- `GET /brands`: Retrieve competitive landscape data.
- `GET /winners`: Access statistically proven winning ad assets.
- `GET /health`: Monitor system costs and operational status.

### 👁️ Visual Clone Detection
Integrated a `VectorStore` interface with **CLIP embeddings** to detect creative reuse across competitors and identify high-performing visual hooks.

### ⚡ Technical Stack
- **Frontend**: Streamlit Unified Command Center.
- **Backend**: FastAPI Microservice.
- **Agents**: CLIP (Vision), Gemini 2.0 (Strategy), Market & Alert Agents.
- **Storage**: SQLAlchemy (Postgres Ready) + Alembic Migrations.

### 👁️ Visual Intelligence (Phase 3)
- **CLIP Embeddings**: Uses OpenAI's CLIP (ViT-B-32) via `sentence-transformers` to generate 512-dimensional visual embeddings for every archived creative.
- **Visual Deduplication**: Enables detection of winner reuse and visual clones across competitors.

### 📈 Tactical Intelligence Layer (Phase 2)
- **Deep Classification**: Extracts 10+ strategic metrics including Urgency Score, Persona mapping, Hook types, and Brand Color analysis.
- **Funnel Mapping**: Captures the true destination landing page and classifies the funnel stage (VSL, DTC, Lead Magnet).

### ⚡ Performance & Reliability
- **Fully Asynchronous**: Converted all sync `requests` to `aiohttp` to prevent worker blocking and scheduler stalls.
- **Smart Archiving**: PIL-based extension detection and SHA-256 content hashing for permanent, deduplicated media storage.
- **Database Migrations**: Integrated Alembic for safe, production-ready schema evolutions.

---

## 🏗️ Architecture Summary

- **UI Layer**: Streamlit Unified Command Center.
- **Executor**: Async Scrapers (Playwright) + Vision Engine (CLIP).
- **Intelligence**: Gemini 2.0 Flash (Multimodal) + CLIP.
- **Persistence**: SQLAlchemy (PostgreSQL ready) with Alembic migrations.
- **Automation**: Multi-threaded Background Worker with Autonomous Recovery.
