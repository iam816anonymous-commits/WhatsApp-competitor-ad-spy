import streamlit as st
import logging
from queue import Queue
from threading import Thread
from dotenv import load_dotenv

from app.ui.dashboard import render_ui
from app.workers.scheduler import background_worker
from app.db.database import engine
from app.models.models import Base
from app.api.main import app as fastapi_app, set_task_queue
import uvicorn

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
    set_task_queue(q)

    # Run FastAPI in a separate thread if needed, or just focus on Streamlit for orchestration
    # For enterprise tier, we run both
    def run_api():
        import socket
        def is_port_in_use(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0

        target_port = 8000
        if is_port_in_use(target_port):
            logging.info(f"Port {target_port} already in use. Attempting 8001.")
            target_port = 8001
            if is_port_in_use(target_port):
                logging.error(f"Port {target_port} also in use. API server will not start.")
                return

        uvicorn.run(fastapi_app, host="0.0.0.0", port=target_port)

    api_thread = Thread(target=run_api, daemon=True)
    api_thread.start()

    render_ui(q)

if __name__ == "__main__":
    main()
