# app/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
import logging

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Define the SQLite database file path
#DATABASE_URL = settings.DATABASE_URL # e.g., "sqlite+aiosqlite:///./mentions.db"
DATABASE_URL ="sqlite+aiosqlite:///./mentions.db"

logger.info(DATABASE_URL) # For debugging, remove in production
# Create the async engine for SQLite
engine = create_async_engine(DATABASE_URL, echo=True) # echo=True logs SQL statements

# Create a configured "Session" class
# expire_on_commit=False is often useful with async sessions and background tasks
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for declarative models
Base = declarative_base()

# Dependency to get DB session in API endpoints
async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Function to initialize the database (create tables)
async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment to drop tables on startup
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if they didn't exist).")