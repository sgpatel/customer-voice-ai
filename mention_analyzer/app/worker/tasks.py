# app/worker/tasks.py
import traceback
from celery import shared_task
from app.services import llm_analyzer
from app.db.database import get_db_session # Assume you have a way to get a DB session in tasks
from app.db.crud import mentions as crud_mentions # CRUD operations module
from app.models.domain.mentions import ProcessingStatus
from app.core.config import logger
import uuid

@shared_task(bind=True, max_retries=3, default_retry_delay=60) # Configure retries for task execution
def analyze_mention_task(self, mention_id: str, mention_text: str):
    """
    Celery task to analyze a mention asynchronously.
    """
    logger.info(f"Task started for mention_id: {mention_id}")
    mention_uuid = uuid.UUID(mention_id)

    async def run_analysis(): # Helper async function to manage DB session
        async with get_db_session() as db:
            try:
                # 1. Mark as processing
                await crud_mentions.update_mention_status(db, mention_uuid, ProcessingStatus.PROCESSING)
                logger.info(f"Marked mention {mention_id} as processing.")

                # 2. Perform analysis
                analysis_result = llm_analyzer.analyze_mention_with_llm(mention_text)
                logger.info(f"LLM analysis successful for mention {mention_id}.")

                # 3. Update DB with results and mark as completed
                await crud_mentions.update_mention_analysis(
                    db=db,
                    mention_id=mention_uuid,
                    analysis_data=analysis_result,
                    status=ProcessingStatus.COMPLETED
                )
                logger.info(f"Successfully processed and stored analysis for mention {mention_id}.")
                return {"status": "Success", "mention_id": mention_id}

            except Exception as e:
                logger.error(f"Task failed for mention_id {mention_id}: {e}", exc_info=True)
                error_msg = traceback.format_exc() # Get detailed error traceback

                # Mark as failed in DB
                try:
                     async with get_db_session() as fail_db: # Use a new session for failure update
                        await crud_mentions.update_mention_status(
                            db=fail_db,
                            mention_id=mention_uuid,
                            status=ProcessingStatus.FAILED,
                            error_message=str(e)[:500] # Store truncated error
                        )
                except Exception as db_err:
                     logger.error(f"CRITICAL: Failed to update mention {mention_id} status to FAILED: {db_err}")


                # Retry logic for Celery task itself (if applicable, e.g., temporary infra issue)
                try:
                    # self.request.retries counts how many times this task instance has been retried
                    logger.warning(f"Retrying task for mention {mention_id} (Attempt {self.request.retries + 1}/{self.max_retries})")
                    # Exponential backoff is handled by Celery based on default_retry_delay
                    raise self.retry(exc=e)
                except self.MaxRetriesExceededError:
                    logger.error(f"Max retries exceeded for mention_id {mention_id}. Marking as failed.")
                    # Final attempt to mark as failed if not already done
                    # (Already handled above, but good as a safeguard)
                    return {"status": "Failed", "mention_id": mention_id, "error": str(e)}

    # Run the async helper function within the sync Celery task context
    # Note: Running async code inside sync Celery tasks needs careful handling.
    # Consider using 'asyncio.run()' or libraries like 'celery-aiorw' if needed,
    # or structuring the DB access differently depending on your DB driver's sync/async nature.
    # This example assumes `get_db_session` provides an async context manager
    # and `asyncio.run` or similar is used appropriately if needed.
    import asyncio
    try:
        return asyncio.run(run_analysis())
    except Exception as e:
        logger.critical(f"Async execution wrapper failed for task {mention_id}: {e}", exc_info=True)
        # Attempt to mark as failed directly here if run_analysis didn't catch it
        # (Should ideally be caught within run_analysis)
        return {"status": "Failed", "mention_id": mention_id, "error": "Async execution wrapper error"}