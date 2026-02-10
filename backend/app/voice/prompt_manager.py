"""
Prompt Manager for handling provider/specialty specific prompts and versioning.
"""
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

from app.voice.prompts import PRE_VERIFICATION_PROMPT

# Base Prompt (v1)
BASE_SYSTEM_PROMPT = PRE_VERIFICATION_PROMPT

class PromptManager:
    def __init__(self):
        # In real app, load from DB or Redis
        self._prompts: Dict[str, str] = {
            "default": BASE_SYSTEM_PROMPT
        }
        
    def get_system_prompt(self, provider_id: Optional[str] = None, specialty: Optional[str] = None) -> str:
        """
        Get the most specific system prompt available.
        Fallback: Provider -> Specialty -> Default.
        """
        key = "default"
        if provider_id and f"provider:{provider_id}" in self._prompts:
            key = f"provider:{provider_id}"
        elif specialty and f"specialty:{specialty}" in self._prompts:
            key = f"specialty:{specialty}"
            
        return self._prompts.get(key, BASE_SYSTEM_PROMPT)

    def update_prompt(self, key: str, content: str):
        """Update a prompt version."""
        self._prompts[key] = content
        # Log to Weave/DB here
