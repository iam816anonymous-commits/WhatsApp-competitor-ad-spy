# 🛠️ Installation & Execution Guide (Windows)

Follow these steps to set up and run the Competitor Ad Spy Agent in your local environment.

## 1. Environment Setup

### Install Dependencies
Ensure you have Python 3.9+ installed, then run:
```bash
pip install -r requirements.txt
```

### Initialize Playwright
Install the required browser binaries:
```bash
playwright install chromium
```

## 2. Configuration

Create a `.env` file in the root directory (or update the `AIConfig` and `BrowserConfig` classes in `app.py`):

- **GEMINI_API_KEY**: Your Google AI Studio API key.
- **CHROME_USER_DATA_PATH**: The local path to your Chrome profile (e.g., `C:\Users\<YourUser>\AppData\Local\Google\Chrome\User Data`). This allows the agent to bypass some login challenges.

## 3. Execution

### Start the Frontend & Background Worker
The Streamlit application initializes the background orchestration thread automatically upon startup.
```bash
streamlit run app.py
```

### Background Worker Operations
- **Scheduler**: Runs every 60 seconds to check for pending jobs.
- **Maintenance**: Runs every 24 hours to prune media files older than 90 days.
- **Logs**: Monitor `agent.log` for real-time operation status.

## 4. Maintenance & Monitoring

| Target | Description |
| :--- | :--- |
| `ad_spy.db` | The main SQLite database containing all ad data and AI analyses. |
| `./media_archive/` | Local storage for archived images/thumbnails (SHA-256 named). |
| `agent.log` | Central log file for both the Streamlit UI and the Scraper worker. |
| `System Health` Tab | In-app dashboard to monitor thread status and scrape error rates. |
