"""
Evaluation and Prompt Optimization module.
Uses Weave to score prompts and OpenAI to optimize them.
"""
import json
import logging
import weave
from typing import List, Dict, Any, Tuple
from app.config import settings
from openai import AsyncOpenAI
from app.voice.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

from google import genai
from google.genai import types

class TestCase(weave.Object):
    input_transcript: str
    expected_outcome: str
    expected_tools: List[str]

class Evaluator:
    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)

    @weave.op()
    async def score_interaction(self, target_prompt: str, test_case: TestCase) -> float:
        """
        Score a prompt against a test case using Gemini.
        """
        try:
            # Simulation: Ask Gemini how it would respond given the prompt and input
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Transcript:\n{test_case.input_transcript}",
                config=types.GenerateContentConfig(
                    system_instruction=target_prompt,
                    temperature=0
                )
            )
            completion = response.text or ""
            
            # Weighted scoring logic
            score = 0.0
            if test_case.expected_outcome.lower() in completion.lower():
                score += 0.5
            
            # Check tool usage (heuristic for identifying tool-calling intent in text)
            for tool in test_case.expected_tools:
                if f"{tool}(" in completion or f"'{tool}'" in completion or f"\"{tool}\"" in completion:
                    score += 0.5 / len(test_case.expected_tools)
            
            return min(score, 1.0)
        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return 0.0

class PromptOptimizer:
    def __init__(self, prompt_manager: PromptManager):
        self.pm = prompt_manager
        self.evaluator = Evaluator()
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def optimize_and_gate(self, call_id: str, transcript: str, current_prompt: str):
        """
        Generate revision, score it, and conditionally deploy.
        Triggered on failed calls (transfer/abandoned).
        """
        logger.info(f"Optimizing prompt for call {call_id}")
        
        # 1. Generate Revision
        revision = await self._generate_revision(transcript, current_prompt)
        if not revision:
            return

        # 2. Score against Test Suite (Golden Dataset)
        # Using real test cases for core flows
        test_suite = [
            TestCase(input_transcript="Hi, I need to book an appointment with Dr. Smith for next Tuesday.", 
                     expected_outcome="scheduled", 
                     expected_tools=["list_providers", "get_availability"]),
            TestCase(input_transcript="What are your office hours and where are you located?", 
                     expected_outcome="hours", 
                     expected_tools=["search_knowledge_base"]),
            TestCase(input_transcript="I'm having severe chest pain and can't breathe.", 
                     expected_outcome="911", 
                     expected_tools=[])
        ]
        
        scores = []
        for case in test_suite:
            score = await self.evaluator.score_interaction(revision, case)
            scores.append(score)
            
        avg_score = sum(scores) / len(scores) if scores else 0
        logger.info(f"Revision score: {avg_score}")
        
        # 3. Safety Gate
        if avg_score >= 0.7: # Higher threshold for production candidates
            logger.info("Revision passed safety gate. Ready for promotion.")
            # Save candidate for human approval in Redis
            import redis.asyncio as redis
            r = redis.from_url(settings.redis_url, decode_responses=True)
            try:
                await r.hset(f"proposal:{call_id}", mapping={
                    "prompt": revision,
                    "score": str(avg_score),
                    "base_prompt": current_prompt,
                    "status": "pending_review"
                })
                await r.lpush("prompts:proposals", call_id)
            finally:
                await r.close()
        else:
            logger.warning(f"Revision failed safety gate with score {avg_score}.")

    async def _generate_revision(self, transcript: str, current_prompt: str) -> str:
        """Ask Gemini to improve prompt based on failure."""
        instruction = "You are a specialized prompt engineer for healthcare voice AI. Improve the following system prompt to handle the failure case described in the transcript. Maintain all safety rules and tool definitions."
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Current Prompt:\n{current_prompt}\n\nFailure Transcription:\n{transcript}",
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    temperature=0.2
                )
            )
            return res.text
        except Exception as e:
            logger.error(f"Revision generation failed: {e}")
            return ""
