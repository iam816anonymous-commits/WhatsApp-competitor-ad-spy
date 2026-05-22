# 🛠️ Installation & Execution Guide

## 1. Environment Setup

### Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### Configuration
1. Rename `.env.example` to `.env`.
2. Update `GEMINI_API_KEY` and `DATABASE_URL`.
3. (Optional) Set `CHROME_USER_DATA_PATH` for persistent browser sessions.

## 2. Database Initialization

This project uses Alembic for migrations.
```bash
# Initialize/Upgrade database to latest schema
alembic upgrade head
```

## 3. Execution

### Start the OS
```bash
streamlit run main.py
```

## 4. Maintenance

- **Media**: Archived in `./media_archive/`.
- **Logs**: Real-time activity in `agent.log`.
- **Migrations**: Create new versions with `alembic revision --autogenerate -m "description"`.
