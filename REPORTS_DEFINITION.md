# 📊 Intelligence Reports Definition

This document outlines the data schemas and formatting standards for all reporting outputs produced by the Competitor Ad Spy Agent.

## 1. High-Signal WhatsApp Mobile Digest

**Trigger**: Manually via UI or Automatically when a "Winning Core Asset" is identified.

### Formatting Guidelines:
- **Header**: `*🏆 WINNING AD ALERT: [Competitor Name]*` or `*🕵️ Ad Intelligence Digest: [Competitor Name]*`
- **Metadata**: `📅 _Generated: [Timestamp]_`
- **Body Sections**:
    - `🔥 *Winning Core Assets Detected (Active > 21 Days):*` (Bulleted list of ad text snippets)
    - `📈 *Market Intelligence:*` (The raw Gemini-generated analysis text)
- **Footer**: `🚀 _Sent by Competitor Ad Spy Agent_`

---

## 2. In-App/Database Intelligence Schema (`ExtractedAds`)

The system maintains a permanent strategic record of the following visual and tactical data:

| Column | Definition |
| :--- | :--- |
| `funnel_type` | Classification: DTC, VSL/Webinar, Lead Magnet, Advertorial, etc. |
| `final_destination_url` | Resolved outbound link after deobfuscation. |
| `ad_text` | Raw copy from the ad creative. |
| `launch_date` | First seen date used for longevity heuristics. |
| `local_media_path` | Path to SHA-256 archived creative. |
| `visual_analysis` | (Stored in `ScrapeRun.analysis_text`) OCR data, color palettes, and visual marketing angles. |

---

## 3. On-Demand Excel Export Framework

**Function**: Stakeholder-facing data export.

### Schema Layout:
1.  **ID**: Unique record identifier.
2.  **Competitor**: Brand/Query name.
3.  **Longevity Status**: Testing / Scaling / Winning Core Asset.
4.  **Age (Days)**: Calculated active duration.
5.  **Funnel Type**: AI-classified funnel category.
6.  **Destination**: Resolved landing page URL.
7.  **Launch Date**: Raw date from the ad library.
8.  **Ad Text**: Truncated copy for readability.
9.  **Media Link**: Local archive path for internal reference.

### Formatting:
- **Sheet Name**: `Ad Intelligence`
- **File Name**: `ad_intelligence_YYYYMMDD.xlsx`
- **Engine**: `openpyxl` (Pandas wrapper)
