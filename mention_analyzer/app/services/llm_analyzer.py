# app/services/llm_analyzer.py
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
import backoff  # For exponential backoff retries
from app.core.config import settings, logger
from app.models.domain.mentions import MentionAnalysis
from typing import Type

# Configure OpenAI client (do this once)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Define retry strategy for transient OpenAI errors
@backoff.on_exception(backoff.expo,
                      (RateLimitError, APITimeoutError, APIError),
                      max_tries=3,
                      jitter=backoff.full_jitter)
def analyze_mention_with_llm(mention_text: str, personality: str = "neutral") -> MentionAnalysis:
    """
    Analyzes a mention using the configured OpenAI model and returns structured data.
    Includes retry logic for common transient API errors.
    """
    logger.info(f"Analyzing mention: '{mention_text[:50]}...'")
    try:
        completion = client.beta.chat.completions.parse(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": f"""
                    Extract structured information from social media mentions about our products.
                    Your persona is {personality}.

                    Identify:
                    - The product mentioned (website, app, not_applicable).
                    - The mention's sentiment (positive, negative, neutral).
                    - Whether a response is needed (true/false). Avoid responding to inflammatory content or clear bait.
                    - A customized response draft if needed.
                    - A concise description for a support ticket if the issue requires developer attention (e.g., bug report, feature request).
                """},
                {"role": "user", "content": mention_text},
            ],
            response_format=MentionAnalysis, # Use the Pydantic model directly
            temperature=0.2, # Lower temperature for more deterministic analysis
        )
        analyzed_data = completion.choices[0].message.parsed
        logger.info(f"Analysis complete for mention: '{mention_text[:50]}...'")
        return analyzed_data

    except APIError as e:
        logger.error(f"OpenAI API Error analyzing mention: {e}", exc_info=True)
        raise  # Re-raise after logging (backoff will catch specific types)
    except Exception as e:
        logger.error(f"Unexpected error analyzing mention '{mention_text[:50]}...': {e}", exc_info=True)
        # Decide how to handle non-API errors - maybe raise a custom exception
        raise ValueError(f"Failed to analyze mention due to unexpected error: {e}")