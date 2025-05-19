from sqlalchemy import create_engine, QueuePool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

db_uri = str(settings.DATABASE_URI)

# Create SQLAlchemy engine
engine = create_engine(
    db_uri,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


# Function to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db():
    import time
    from sqlalchemy.exc import OperationalError
    from sqlalchemy import text

    max_retries = 30
    retry = 0
    while retry < max_retries:
        try:
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            return
        except OperationalError:
            retry += 1
            print(f"Waiting for database... Retry {retry}/{max_retries}")
            time.sleep(2)

    raise Exception("Could not connect to the database after multiple retries")


# Function to create tables
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)
