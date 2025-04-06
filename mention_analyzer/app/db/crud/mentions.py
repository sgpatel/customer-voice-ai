# app/db/crud/mentions.py
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import select, desc, update, func, case
from app.models.db.mentions import MentionDB
from app.models.domain.mentions import MentionCreate, MentionAnalysis, ProcessingStatus
from app.core.config import logger
import datetime

async def create_mention(db: AsyncSession, mention: MentionCreate) -> MentionDB:
    """Creates a new mention record in the database."""
    db_mention = MentionDB(
        text=mention.text,
        source=mention.source,
        metadata_=mention.metadata, # Map to db column name
        status=ProcessingStatus.PENDING
    )
    db.add(db_mention)
    # Commit is usually handled by the caller (endpoint) after adding task
    # await db.commit()
    # await db.refresh(db_mention) # Refresh needed after commit
    logger.info(f"Adding mention to session: Text='{mention.text[:50]}...'")
    return db_mention

async def get_mention(db: AsyncSession, mention_id: uuid.UUID) -> MentionDB | None:
    """Retrieves a mention by its ID."""
    result = await db.execute(select(MentionDB).filter(MentionDB.id == mention_id))
    return result.scalars().first()

async def update_mention_status(db: AsyncSession, mention_id: uuid.UUID, status: ProcessingStatus, error_message: str | None = None):
    """Updates the status and optionally error message of a mention."""
    logger.info(f"Updating mention {mention_id} status to {status}")
    stmt = (
        update(MentionDB)
        .where(MentionDB.id == mention_id)
        .values(
            status=status,
            error_message=error_message,
            updated_at=datetime.datetime.now(datetime.timezone.utc)
         )
        # .execution_options(synchronize_session="fetch") # May be needed depending on SQLAlchemy version/context
    )
    await db.execute(stmt)
    # Commit handled by the background task function itself

async def update_mention_analysis(db: AsyncSession, mention_id: uuid.UUID, analysis_data: MentionAnalysis, status: ProcessingStatus):
    """Updates a mention with analysis results and sets status."""
    logger.info(f"Updating mention {mention_id} with analysis results, status {status}")
    analysis_dict = analysis_data.model_dump() # Convert Pydantic model to dict for JSON storage
    stmt = (
        update(MentionDB)
        .where(MentionDB.id == mention_id)
        .values(
            analysis_result=analysis_dict,
            status=status,
            product=analysis_data.product, # Also store key fields directly if needed
            sentiment=analysis_data.sentiment,
            needs_response=analysis_data.needs_response,
            error_message=None, # Clear previous errors on success
            updated_at=datetime.datetime.now(datetime.timezone.utc)
        )
        # .execution_options(synchronize_session="fetch")
    )
    await db.execute(stmt)
     # Commit handled by the background task function itself


# --- ADD THIS FUNCTION ---
async def get_mentions(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[MentionDB]:
    """
    Retrieves a list of mentions from the database.

    Args:
        db: The AsyncSession instance.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        A list of MentionDB ORM objects.
    """
    result = await db.execute(
        select(MentionDB)
        .order_by(desc(MentionDB.created_at)) # Order by creation date, newest first
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
# --- END OF FUNCTION TO ADD ---


# --- ADD THIS FUNCTION ---
async def get_mention_summary(db: AsyncSession) -> dict:
    """
    Calculates summary statistics for mentions.

    Returns:
        A dictionary containing counts by status and sentiment.
    """
    logger.info("Calculating mention summary statistics.")

    # Query for counts per status
    status_query = (
        select(
            MentionDB.status,
            func.count(MentionDB.id).label("count")
        )
        .group_by(MentionDB.status)
    )
    status_result = await db.execute(status_query)
    status_counts = {row.status.value: row.count for row in status_result.all()}

    # Query for counts per sentiment (only for 'completed' mentions)
    # We access sentiment from the JSON 'analysis_result' field
    # Note: JSON querying can vary slightly between DB backends. This works for SQLite/PostgreSQL.
    sentiment_query = (
        select(
            # Use ->> to extract JSON field as text
            func.json_extract(MentionDB.analysis_result, '$.sentiment').label("sentiment"),
            func.count(MentionDB.id).label("count")
        )
        .where(MentionDB.status == ProcessingStatus.COMPLETED) # Only completed mentions have sentiment
        .where(func.json_extract(MentionDB.analysis_result, '$.sentiment') != None) # Ensure sentiment exists
        .group_by(func.json_extract(MentionDB.analysis_result, '$.sentiment'))
    )

    sentiment_result = await db.execute(sentiment_query)
    sentiment_counts = {row.sentiment: row.count for row in sentiment_result.all()}

    # Get total count
    total_count_result = await db.execute(select(func.count(MentionDB.id)))
    total_count = total_count_result.scalar_one_or_none() or 0

    summary = {
        "total_mentions": total_count,
        "by_status": {
            # Ensure all statuses are present, defaulting to 0
            status.value: status_counts.get(status.value, 0)
            for status in ProcessingStatus
        },
        "by_sentiment": sentiment_counts # Only includes sentiments found
    }
    logger.info(f"Summary calculated: {summary}")
    return summary
# --- END OF FUNCTION TO ADD ---

# ... rest of the CRUD functions ...