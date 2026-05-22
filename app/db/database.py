import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///ad_spy.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30} if "sqlite" in DATABASE_URL else {},
    pool_size=20,
    max_overflow=40
)
SessionLocal = sessionmaker(bind=engine)

def get_session():
    return SessionLocal()
