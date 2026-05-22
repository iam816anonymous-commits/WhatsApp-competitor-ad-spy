# 🕵️ AdSpy AI: Competitor Intelligence OS

An enterprise-grade AI agent system for autonomous competitor intelligence, multi-platform scraping, and predictive marketing analytics.

## 🚀 Key Upgrades (v2.0 Modular)

### 🏗️ Modular Micro-Architecture
The application has been refactored from a monolithic script into a professional multi-package system:
- `app/agents`: Domain-specific AI agents (Vision, Strategy, Scraper).
- `app/db`: Database connectivity and session management.
- `app/models`: SQLAlchemy 2.0 type-safe models.
- `app/scrapers`: Multi-platform extraction engines.
- `app/ui`: Streamlit frontend components.
- `app/utils`: Asynchronous media processing and link deobfuscation.
- `app/workers`: Background task orchestration and scheduling.

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
