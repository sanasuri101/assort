"""
Script to run automated evaluations using Weave.
"""
import asyncio
import json
import logging
import weave
from app.learning.evals import Evaluator, TestCase
from app.voice.prompt_manager import PromptManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evals")

async def main():
    # Load dataset
    with open("tests/data/golden_conversations.json", "r") as f:
        data = json.load(f)
    
    test_suite = [TestCase(**item) for item in data]
    
    # Init Weave
    # weave.init("assort-health") 
    
    # Load current prompt
    pm = PromptManager()
    current_prompt = pm.get_system_prompt()
    
    evaluator = Evaluator()
    scores = []
    
    logger.info(f"Running evaluation on {len(test_suite)} test cases...")
    
    for case in test_suite:
        score = await evaluator.score_interaction(current_prompt, case)
        scores.append(score)
        logger.info(f"Test case score: {score}")
        
    avg = sum(scores) / len(scores) if scores else 0
    logger.info(f"Average Score: {avg:.2f}")
    
    if avg >= 0.5:
        logger.info("✅ System Prompt passed safety gate.")
    else:
        logger.error("❌ System Prompt failed safety gate.")

if __name__ == "__main__":
    asyncio.run(main())
