# 🕵️ Competitor Ad Spy AI Agent

An enterprise-ready, modular AI agent system designed for autonomous competitor intelligence, multi-channel ad scraping, and predictive marketing analytics.

## 🚀 Elite-Tier Capabilities

### 👁️ Multimodal Visual Insights
Powered by **Gemini 2.0 Flash**, the agent performs deep visual analysis of ad creatives. It executes OCR on embedded text and identifies branding styles, color palettes, and visual marketing hooks to uncover the "why" behind high-performing creatives.

### 🔗 Outbound Link Deobfuscation
The agent automatically follows Meta's obfuscated redirect links (`fb.me`, `l.php`) to resolve the **true final destination URL**. This allows for precise mapping of competitor funnels (Shopify pages, VSLs, Advertorials).

### 📈 Predictive Ad Longevity Heuristics
Using statistical longevity modeling, the system categorizes ads into **Testing**, **Scaling**, or **Winning Core Assets**. It filters out the noise, alerting you only when a competitor has found a proven "winner."

### 📂 Local Media Archiving (SHA-256)
Meta's CDN links expire, but your intelligence shouldn't. The agent downloads and archives all ad media locally using **SHA-256 content hashing** for zero-duplication storage and permanent accessibility.

---

## ⚙️ Technical Workflow Loop

1.  **Schedule**: The autonomous background scheduler monitors the SQLite database for due monitoring tasks.
2.  **Scrape**: The `BaseScraper` framework initializes a stealth Playwright instance to navigate ad libraries (Meta, TikTok) and extract raw data.
3.  **Analyze**: Raw text, resolved URLs, and archived images are passed to the Gemini Multimodal engine for strategic classification.
4.  **Digest**: High-signal insights are formatted into an intelligence digest and delivered via WhatsApp or accessible via the Streamlit Command Center.

---

## 🏗️ Architecture Summary

- **UI Layer**: Streamlit Unified Command Center.
- **Extraction**: Stealth Playwright with automated redirect resolution.
- **Intelligence**: Gemini 2.0 Flash (Multimodal).
- **Persistence**: SQLAlchemy (SQLite) with SHA-256 media archiving.
- **Automation**: Multi-threaded background worker with autonomous recovery.
