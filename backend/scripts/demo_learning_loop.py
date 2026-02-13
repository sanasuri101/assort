import os
import sys
import asyncio
import json
import logging
import weave
from datetime import datetime

# Add the backend directory to the search path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.learning.analysis import CallAnalyzer, CallAnalysis
from app.learning.evals import PromptOptimizer
from app.voice.prompt_manager import PromptManager

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure WANDB_API_KEY is set for Weave
if settings.wandb_api_key:
    os.environ["WANDB_API_KEY"] = settings.wandb_api_key

async def run_scenario_1():
    """Scenario 1: Success/Knowledge Extraction"""
    print("\n" + "="*60)
    print("SCENARIO 1: Successful Call -> Knowledge Extraction")
    print("="*60)

    transcript = """
👤 User: Hi, I'm calling to schedule an appointment with Dr. Aris.
🤖 Assistant: Of course! I can help with that. First, I need to verify your identity. Could you please provide your full name and date of birth?
👤 User: Yes, it's Sarah Jones, born March 12, 1985.
🤖 Assistant: Thank you, Sarah. I see you're in our system. Dr. Aris has an opening next Thursday at 2:00 PM. Does that work for you?
👤 User: That works. Also, does Dr. Aris validate parking? I'm coming from the North side.
🤖 Assistant: Let me check... Dr. Aris does provide parking validation for the deck on Main Street. I've booked your appointment for Thursday at 2:00 PM.
👤 User: Great, thank you!
    """

    analyzer = CallAnalyzer()
    print("Analyzing transcript and extracting insights...")
    analysis: CallAnalysis = await analyzer.analyze_transcript("demo-call-success", transcript)

    print(f"\nSummary: {analysis.summary}")
    print(f"Outcome: {analysis.outcome}")
    print(f"Sentiment: {analysis.sentiment}")
    
    if analysis.knowledge_candidates:
        print(f"\n💡 Extracted {len(analysis.knowledge_candidates)} Knowledge Candidates:")
        for cand in analysis.knowledge_candidates:
            print(f"- Q: {cand.question}")
            print(f"  A: {cand.answer} (Confidence: {cand.confidence})")
    else:
        print("\nNo new knowledge candidates identified.")

async def run_scenario_2():
    """Scenario 2: Failure/Optimization"""
    print("\n" + "="*60)
    print("SCENARIO 2: Failed Call -> Prompt Optimization")
    print("="*60)

    transcript = """
👤 User: I need to know if you accept 'Blue Shield Premier' specifically.
🤖 Assistant: We accept most major Blue Shield plans. Would you like to schedule?
👤 User: No, Blue Shield Premier is very different from the standard ones. Do you specifically accept the Premier tier?
🤖 Assistant: I'm not sure about that specific tier. I can check with the office manager if you'd like.
👤 User: Usually medical offices know this. It's frustrating. Never mind, I'll call somewhere else.
    """

    pm = PromptManager()
    optimizer = PromptOptimizer(pm)
    
    current_prompt = pm.get_system_prompt()
    
    print("Call resulted in frustration. Triggering Optimization Loop...")
    print("1. Generating revised prompt based on failure...")
    print("2. Running W&B Weave Safety Gate (Evaluator)...")
    
    # This will generate a revision, score it, and if >0.7, save it to Redis
    await optimizer.optimize_and_gate("demo-call-failure", transcript, current_prompt)
    
    print("\nOptimization process complete. Check the Weave dashboard for traces.")
    print("If the score was high enough, a 'proposal:demo-call-failure' was saved to Redis.")

async def main():
    # Initialize Weave for the demo
    weave.init(f"assort-health-demo-{settings.practice_name.lower().replace(' ', '-')}")
    print("Starting Healthcare Learning Loop Demo...")
    
    try:
        await run_scenario_1()
        await run_scenario_2()
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
    
    print("\nDemo Finished!")

if __name__ == "__main__":
    asyncio.run(main())
