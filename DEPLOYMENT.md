# Market Intelligence OS - Advanced Deployment

This document details the high-level architecture and operational procedures for the Market Intelligence platform.

## 1. Architecture Overview

The system is designed as a **Modular Monolith** with the following layers:

*   **UI Layer (`app/ui/`):** Streamlit-based dashboard for visualization and human-in-the-loop control.
*   **API Layer (`app/api/`):** FastAPI service providing programmatic access to scrapes, analysis, and data.
*   **Agent Layer (`app/agents/`):**
    *   `Collector`: Meta Ad Library scraper.
    *   `AI Agent`: Gemini 2.0 Multimodal analyzer.
    *   `Vision Agent`: CLIP-based creative embedding and visual search.
    *   `Strategy Agent`: Funnel and landing page intelligence.
    *   `Analyst Agent`: Market Pulse synthesis and trend detection.
    *   `Prediction Agent`: Winner probability and fatigue forecasting.
*   **Data Layer (`app/db/`):** SQLAlchemy 2.0 Knowledge Graph on SQLite (migratable to Postgres).
*   **Worker Layer (`app/workers/`):** Asynchronous task processing using Python `Queue` and `threading`.

## 2. Key Intelligence Features

### Multimodal Extraction
The platform uses Gemini 2.0 Flash to simultaneously analyze ad copy, perform OCR on images, and decode visual hierarchy to identify hook types, offer structures, and target personas.

### Creative Cloning Detection
Visual embeddings (CLIP) allow the system to detect when a brand "clones" a successful creative from a competitor. The `VectorStore` calculates cosine similarity between all archived media.

### Predictive Fatigue
By tracking the `launch_date` and `last_seen` timestamps, the system calculates the "Ad Survival Rate." The `PredictionAgent` uses this to estimate when a creative is likely to fatigue.

### Enterprise Cost Governor
Integrated budget tracking ensures that AI inference costs never exceed the organization's monthly limit.

## 3. Deployment & Scaling

### Database Migrations
Always use Alembic for schema changes:
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Benchmarking
To verify AI extraction accuracy:
```bash
python -m tests.benchmarks.ai_benchmark
```

## 4. Environment Variables
* `GEMINI_API_KEY`: Required for multimodal analysis.
* `DATABASE_URL`: Defaults to `sqlite:///adspy.db`.
