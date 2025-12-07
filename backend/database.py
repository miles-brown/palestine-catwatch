
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os
from dotenv import load_dotenv

load_dotenv()

# Use Postgres URL from env, or valid default
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/protest_db"

# Fix for SQLAlchemy 1.4+ which deprecated 'postgres://'
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Log URL structure for debugging (masking sensitive info)
# This helps identify if the URL is malformed or empty in logs
safe_url = SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else "local_or_no_auth"
print(f"Attempting DB connection to: ...@{safe_url}")
# Fallback to sqlite if needed for tests without docker, but prefer PG
# SQLALCHEMY_DATABASE_URL = "sqlite:///./protest_monitor.db"

# Neon/Railway optimization: 
# pool_pre_ping=True checks if connection is alive before using it (fixes SSL closed error)
# pool_recycle=300 recycles connections every 5 mins to prevent stale timeouts
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=10,
    max_overflow=20
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
