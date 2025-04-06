# app/api/v1/endpoints/mentions.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any # Ensure List is imported for the response model

# Import the factory and dependency function for DB sessions
from app.db.database import get_db_session, AsyncSessionLocal
# Import CRUD functions for database operations
from app.db.crud import mentions as crud_mentions
# Import Pydantic models used for API requests/responses and domain logic
from app.models.domain.mentions import MentionCreate, MentionRecord, MentionAnalysis, ProcessingStatus, MentionSummary
# Import the service performing the LLM analysis
from app.services import llm_analyzer
# Import logger
from app.core.config import logger
import uuid
import traceback
import asyncio # Needed if using asyncio.to_thread for sync LLM calls

# Define the FastAPI router
router = APIRouter()

# --- Background Task Function ---
# This function runs the analysis in the background.
# It needs to manage its own database session.
async def run_analysis_background(mention_id: uuid.UUID, mention_text: str):
    """
    Performs mention analysis asynchronously in the background.
    Handles database session, status updates, LLM call, and error logging.
    """
    logger.info(f"Background task started for mention_id: {mention_id}")
    # Create a new database session specifically for this background task
    async with AsyncSessionLocal() as db: # Get a new session using the factory
        try:
            # 1. Mark as processing in the database
            await crud_mentions.update_mention_status(db, mention_id, ProcessingStatus.PROCESSING)
            await db.commit() # Commit status change
            logger.info(f"Marked mention {mention_id} as processing (background task).")

            # 2. Perform the actual analysis using the LLM service
            # If llm_analyzer.analyze_mention_with_llm uses the SYNC OpenAI client,
            # run it in a thread pool to avoid blocking the async event loop.
            try:
                analysis_result = await asyncio.to_thread(llm_analyzer.analyze_mention_with_llm, mention_text)
            except Exception as llm_err:
                 logger.error(f"LLM analysis failed directly for {mention_id}: {llm_err}", exc_info=True)
                 raise # Re-raise to be caught by the outer try/except block

            # If llm_analyzer.analyze_mention_with_llm was modified to use an ASYNC OpenAI client:
            # analysis_result = await llm_analyzer.analyze_mention_with_llm(mention_text)

            logger.info(f"LLM analysis successful for mention {mention_id} (background task).")

            # 3. Update DB with analysis results and mark as completed
            await crud_mentions.update_mention_analysis(
                db=db,
                mention_id=mention_id,
                analysis_data=analysis_result, # analysis_result is a MentionAnalysis Pydantic model
                status=ProcessingStatus.COMPLETED
            )
            await db.commit() # Commit final results
            logger.info(f"Successfully processed and stored analysis for mention {mention_id} (background task).")

        except Exception as e:
            # Handle errors during the background task
            logger.error(f"Background task failed for mention_id {mention_id}: {e}", exc_info=True)
            await db.rollback()
            try:
                await crud_mentions.update_mention_status(
                    db=db,
                    mention_id=mention_id,
                    status=ProcessingStatus.FAILED,
                    error_message=str(e)[:500] # Store truncated error message
                )
                await db.commit() # Commit the failure status
            except Exception as db_err:
                 logger.critical(f"CRITICAL: Failed to update mention {mention_id} status to FAILED in background task: {db_err}")

# --- API Endpoint to List Mentions ---
# Handles GET requests to /api/v1/mentions/
@router.get("/", response_model=List[MentionRecord]) # Ensure this uses @router.get("/")
async def list_mentions(
    skip: int = 0,
    limit: int = 100, # Default to fetching latest 100
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves a list of the latest mentions with their status and results.
    """
    logger.info(f"Fetching list of mentions: skip={skip}, limit={limit}")
    db_mentions_orm = await crud_mentions.get_mentions(db, skip=skip, limit=limit)

    # Validate each ORM object when returning a list
    response_data = []
    for db_mention_orm in db_mentions_orm:
         mention_data_dict = {
            "id": db_mention_orm.id,
            "text": db_mention_orm.text,
            "source": db_mention_orm.source,
            "metadata": db_mention_orm.metadata_ if isinstance(db_mention_orm.metadata_, dict) else None,
            "created_at": db_mention_orm.created_at,
            "updated_at": db_mention_orm.updated_at,
            "status": db_mention_orm.status,
            "analysis_result": db_mention_orm.analysis_result if isinstance(db_mention_orm.analysis_result, dict) else None,
            "error_message": db_mention_orm.error_message,
        }
         response_data.append(MentionRecord.model_validate(mention_data_dict))

    return response_data

# --- API Endpoint to Submit a Mention ---
# Handles POST requests to /api/v1/mentions/
@router.post("/", response_model=MentionRecord, status_code=status.HTTP_202_ACCEPTED)
async def submit_mention_for_analysis(
    mention_in: MentionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Accepts a new mention via POST request. Saves it and schedules background analysis.
    """
    logger.info(f"Received mention submission: source='{mention_in.source}', text='{mention_in.text[:50]}...'")
    try:
        db_mention_orm = await crud_mentions.create_mention(db=db, mention=mention_in)
        await db.commit()
        await db.refresh(db_mention_orm)
        logger.info(f"Mention saved to DB with ID: {db_mention_orm.id} and status: {db_mention_orm.status}")

        background_tasks.add_task(run_analysis_background, db_mention_orm.id, db_mention_orm.text)
        logger.info(f"Scheduled background analysis task for mention ID: {db_mention_orm.id}")

        mention_data_dict = {
            "id": db_mention_orm.id,
            "text": db_mention_orm.text,
            "source": db_mention_orm.source,
            "metadata": db_mention_orm.metadata_ if isinstance(db_mention_orm.metadata_, dict) else None,
            "created_at": db_mention_orm.created_at,
            "updated_at": db_mention_orm.updated_at,
            "status": db_mention_orm.status,
            "analysis_result": db_mention_orm.analysis_result if isinstance(db_mention_orm.analysis_result, dict) else None,
            "error_message": db_mention_orm.error_message,
        }
        response_data = MentionRecord.model_validate(mention_data_dict)
        return response_data

    except Exception as e:
        logger.error(f"Failed to submit mention for analysis: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate mention analysis process."
        )



# --- API Endpoint for Summary Statistics ---
@router.get("/summary", response_model=MentionSummary)
async def get_summary(
    db: AsyncSession = Depends(get_db_session)
):
    """
    Retrieves summary statistics about the mentions, such as counts
    by status and sentiment.
    """
    summary_data = await crud_mentions.get_mention_summary(db)
    if summary_data is None:
         # Should not happen with current logic, but handle defensively
        raise HTTPException(status_code=404, detail="Summary data not available")
    return summary_data
# --- END OF ENDPOINT TO ADD ---

# --- API Endpoint to Get Specific Mention Status ---
# Handles GET requests to /api/v1/mentions/{mention_id}
@router.get("/{mention_id}", response_model=MentionRecord)
async def get_mention_status(
    mention_id: uuid.UUID, # Path parameter for the mention ID
    db: AsyncSession = Depends(get_db_session) # Dependency for DB session
):
    """
    Retrieves the status and analysis results for a specific mention by ID.
    """
    logger.info(f"Fetching status for mention ID: {mention_id}")
    db_mention_orm = await crud_mentions.get_mention(db, mention_id=mention_id)

    if db_mention_orm is None:
        logger.warning(f"Mention ID not found: {mention_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mention not found")

    logger.info(f"Returning status for mention ID: {mention_id}, Status: {db_mention_orm.status}")

    # Apply the same validation fix here
    mention_data_dict = {
        "id": db_mention_orm.id,
        "text": db_mention_orm.text,
        "source": db_mention_orm.source,
        "metadata": db_mention_orm.metadata_ if isinstance(db_mention_orm.metadata_, dict) else None,
        "created_at": db_mention_orm.created_at,
        "updated_at": db_mention_orm.updated_at,
        "status": db_mention_orm.status,
        "analysis_result": db_mention_orm.analysis_result if isinstance(db_mention_orm.analysis_result, dict) else None,
        "error_message": db_mention_orm.error_message,
    }
    response_data = MentionRecord.model_validate(mention_data_dict)
    return response_data

