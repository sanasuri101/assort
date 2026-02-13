"""
Post-call analysis module.
Extracts insights, sentiment, and outcomes from call transcripts using OpenAI.
"""
import json
import logging
import re
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from app.config import settings
import weave

logger = logging.getLogger(__name__)

# --- PII Filter ---

class PIIFilter:
    """Strict PII Redactor."""
    
    # Patterns
    SSN_REGEX = r"\b\d{3}-\d{2}-\d{4}\b"
    PHONE_REGEX = r"\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})\b"
    EMAIL_REGEX = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    # Credit Card (Luhn check is overkill, just match 16 digits)
    CC_REGEX = r"\b(?:\d{4}[- ]?){3}\d{4}\b"
    # Date of Birth (Simple formats)
    DOB_REGEX = r"\b(0[1-9]|1[0-2])[- /](0[1-9]|[12][0-9]|3[01])[- /](19|20)\d{2}\b"

    @classmethod
    def redact(cls, text: str) -> str:
        """Redact PII from text."""
        if not text:
            return ""
        text = re.sub(cls.SSN_REGEX, "[SSN]", text)
        text = re.sub(cls.PHONE_REGEX, "[PHONE]", text)
        text = re.sub(cls.EMAIL_REGEX, "[EMAIL]", text)
        text = re.sub(cls.CC_REGEX, "[CC]", text)
        text = re.sub(cls.DOB_REGEX, "[DOB]", text)
        return text

    @classmethod
    def contains_pii(cls, text: str) -> bool:
        """Check if text contains potential PII."""
        return (
            bool(re.search(cls.SSN_REGEX, text)) or
            bool(re.search(cls.PHONE_REGEX, text)) or
            bool(re.search(cls.EMAIL_REGEX, text)) or
            bool(re.search(cls.CC_REGEX, text)) or
            bool(re.search(cls.DOB_REGEX, text))
        )

# --- Data Models ---

class KnowledgeCandidate(BaseModel):
    question: str = Field(..., description="The user's question (e.g., 'Do you have wifi?')")
    answer: str = Field(..., description="Proposed answer (or empty if unknown)")
    confidence: float = Field(..., description="Confidence in the extraction (0.0-1.0)")
    source_call_id: str

    @field_validator("question", "answer")
    def check_pii(cls, v):
        if PIIFilter.contains_pii(v):
            # For data model, we can warn or redact. 
            # Requirements say "Any candidate containing potential PHI is flagged/dropped"
            # Here we redact it to be safe, but worker might drop it.
            return PIIFilter.redact(v)
        return v

class CallAnalysis(BaseModel):
    call_id: str
    summary: str = Field(..., description="Brief summary of the conversation")
    outcome: str = Field(..., description="Call outcome: 'scheduled', 'answered', 'transferred', 'abandoned', 'emergency'")
    sentiment: str = Field(..., description="User sentiment: 'positive', 'neutral', 'negative', 'frustrated'")
    missing_info: List[str] = Field(default_factory=list, description="Questions the user asked that the bot could not answer")
    compliance_issues: List[str] = Field(default_factory=list, description="Potential HIPAA violations or safety issues")
    knowledge_candidates: List[KnowledgeCandidate] = Field(default_factory=list, description="Proposed Q&A pairs for the knowledge base")

from google import genai
from google.genai import types

class CallAnalyzer:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)

    @weave.op()
    async def analyze_transcript(self, call_id: str, transcript: str) -> CallAnalysis:
        """Analyze transcript using Gemini."""
        
        system_prompt = """
        You are an expert QA analyst for a healthcare voice AI.
        Analyze the following call transcript.
        
        Return a JSON object matching this schema:
        {
            "summary": "Brief summary",
            "outcome": "scheduled|answered|transferred|abandoned|emergency",
            "sentiment": "positive|neutral|negative|frustrated",
            "missing_info": ["item1", "item2"],
            "compliance_issues": ["issue1"],
            "knowledge_candidates": [
                {"question": "...", "answer": "...", "confidence": 0.9}
            ]
        }
        """
        
        try:
            # google-genai generate_content is synchronous in v0.x
            # or we check for async client. 
            # Given the previous context, I'll use to_thread if needed, 
            # but let's see if we can use the async client if available in future.
            # For now, following the user's Client usage.
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Transcript:\n{transcript}",
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0
                )
            )
            
            content = response.text
            if not content:
                raise ValueError("Empty response from Gemini")
                
            data = json.loads(content)
            data["call_id"] = call_id
            
            # Helper to inject source_call_id into candidates before validation
            if "knowledge_candidates" in data:
                for cand in data["knowledge_candidates"]:
                    cand["source_call_id"] = call_id
            
            return CallAnalysis(**data)
            
        except Exception as e:
            logger.error(f"Analysis failed for {call_id}: {e}")
            return CallAnalysis(
                call_id=call_id,
                summary="Analysis failed",
                outcome="unknown",
                sentiment="neutral"
            )
