# app/models/db/mentions.py
import uuid
import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON, Enum as SQLEnum, UUID as SQLUUID
from app.db.database import Base
from app.models.domain.mentions import ProcessingStatus # Use the same Enum

class MentionDB(Base):
    __tablename__ = "mentions"

    # Use UUID as primary key, ensuring compatibility with SQLite
    id = Column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    text = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True) # Use 'metadata_' to avoid keyword conflict

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    error_message = Column(Text, nullable=True)

    # Store analysis results as JSON in the DB for simplicity with SQLite
    # Or create separate columns if you prefer more structured DB querying
    analysis_result = Column(JSON, nullable=True)

    # Potential fields derived from analysis_result for easier querying
    product = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    needs_response = Column(Boolean, nullable=True)