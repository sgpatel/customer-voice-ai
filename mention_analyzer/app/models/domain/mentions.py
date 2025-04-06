# app/models/domain/mentions.py
from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Dict
from enum import Enum
import uuid
import datetime

# Existing Mention analysis structure
class MentionAnalysis(BaseModel):
    product: Literal['app', 'website', 'not_applicable']
    sentiment: Literal['positive', 'negative', 'neutral']
    needs_response: bool
    response: Optional[str] = None
    support_ticket_description: Optional[str] = None

# Model for incoming mention data via API
class MentionCreate(BaseModel):
    text: str = Field(..., min_length=1, description="The raw text of the social media mention")
    source: Optional[str] = Field(None, description="Origin of the mention (e.g., 'twitter', 'web_form')")
    metadata: Optional[dict] = Field(None, description="Any additional context (e.g., user ID, post URL)")

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class MentionRecord(MentionCreate):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    # --- CORRECT THESE LINES ---
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))
    # --- END CORRECTION ---
    status: ProcessingStatus = ProcessingStatus.PENDING
    analysis_result: Optional[MentionAnalysis] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True # For compatibility with ORM models

# --- ADD THIS MODEL ---
class MentionSummary(BaseModel):
    total_mentions: int
    by_status: Dict[str, int] # Explicitly define nested dict structure
    by_sentiment: Dict[str, int]
# --- END OF MODEL TO ADD ---