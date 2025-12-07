import database, models
import time
from sqlalchemy import text

def wait_for_db():
    retries = 5
    while retries > 0:
        try:
            db = database.SessionLocal()
            db.execute(text("SELECT 1"))
            print("✅ Database connection successful.")
            return True
        except Exception as e:
            print(f"Waiting for DB... ({e})")
            retries -= 1
            time.sleep(2)
    return False

if __name__ == "__main__":
    if wait_for_db():
        # strict verification: check if tables exist or creating them works
        try:
            print("Creating tables...")
            models.Base.metadata.create_all(bind=database.engine)
            print("✅ Tables created (or already exist).")
        except Exception as e:
            print(f"❌ Failed to create tables: {e}")
    else:
        print("❌ Could not connect to Database.")
