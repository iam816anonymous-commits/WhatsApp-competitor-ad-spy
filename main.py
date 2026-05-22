import streamlit as st
import logging
from queue import Queue
from threading import Thread
from dotenv import load_dotenv

from app.ui.dashboard import render_ui
from app.workers.scheduler import background_worker
from app.db.database import engine
from app.models.models import Base

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("agent.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Ensure DB tables exist (fallback if not using migrations yet)
Base.metadata.create_all(engine)

@st.cache_resource
def get_task_queue():
    q = Queue()
    worker_thread = Thread(target=background_worker, args=(q,), daemon=True)
    worker_thread.start()
    return q

def main():
    q = get_task_queue()
    render_ui(q)

if __name__ == "__main__":
    main()
