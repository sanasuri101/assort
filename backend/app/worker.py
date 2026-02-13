"""
Worker process for post-call analysis.
Consumes call IDs from Redis Stream, runs analysis, and stores results.
"""
import asyncio
import json
import logging
import signal
import sys
import hashlib
from redis.asyncio import Redis
import weave

from app.config import settings
from app.learning.analysis import CallAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

STOP_EVENT = asyncio.Event()

def handle_sigterm(*args):
    STOP_EVENT.set()

async def process_stream(redis: Redis, analyzer: CallAnalyzer):
    """Consume from Redis Stream and process calls."""
    stream_key = settings.redis_stream_analysis
    group_name = "analysis_workers"
    consumer_name = "worker_1"

    # Create consumer group if not exists
    try:
        await redis.xgroup_create(stream_key, group_name, mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Error creating consumer group: {e}")

    logger.info(f"Worker started. listening on {stream_key}")

    while not STOP_EVENT.is_set():
        try:
            # Block for 1s waiting for new messages
            streams = await redis.xreadgroup(
                group_name, consumer_name, {stream_key: ">"}, count=1, block=1000
            )

            if not streams:
                continue

            for _, messages in streams:
                for message_id, data in messages:
                    call_id = data.get("call_id")
                    if not call_id:
                        await redis.xack(stream_key, group_name, message_id)
                        continue

                    logger.info(f"Processing call: {call_id}")
                    
                    # Fetch transcript from Redis
                    # Assuming bot.py saved it to "call:{call_id}:transcript" or similar
                    # For now, let's fetch from call_state or transcript logs
                    # Ideally, bot.py should store the full transcript list in a known key
                    
                    # Fetch transcript from Redis
                    transcript_key = f"call:{call_id}:transcript"
                    # It's a list (pushed by bot.py)
                    transcript_lines = await redis.lrange(transcript_key, 0, -1)
                    
                    if not transcript_lines:
                        logger.warning(f"No transcript found for {call_id}")
                        await redis.xack(stream_key, group_name, message_id)
                        continue
                        
                    transcript = "\n".join(transcript_lines)

                    # Run analysis
                    analysis = await analyzer.analyze_transcript(call_id, transcript)
                    
                    # Store result
                    result_key = f"analysis:{call_id}"
                    await redis.hset(result_key, mapping=analysis.model_dump(exclude={"knowledge_candidates"}))
                    logger.info(f"Analysis stored for {call_id}: {analysis.outcome}")
                    
                    # Store Knowledge Candidates
                    for cand in analysis.knowledge_candidates:
                        # Double check PII (though validator handles it)
                        if "[SSN]" in cand.question or "[SSN]" in cand.answer:
                           logger.warning(f"Dropping candidate with PII: {cand.question}")
                           continue
                           
                        # Deterministic ID based on question hash
                        q_hash = hashlib.md5(cand.question.encode()).hexdigest()[:10]
                        cand_id = f"cand:{call_id}:{q_hash}"
                        # Store details
                        await redis.hset(cand_id, mapping=cand.model_dump())
                        # Push to review queue
                        await redis.lpush("candidates:knowledge", cand_id)
                        logger.info(f"New candidate queued: {cand.question}")

                    # Acknowledge
                    await redis.xack(stream_key, group_name, message_id)

        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(1)

async def main():
    # Initialize Weave
    if settings.wandb_api_key:
        weave.init("assort-health")
    
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    analyzer = CallAnalyzer()
    
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, handle_sigterm)
    loop.add_signal_handler(signal.SIGTERM, handle_sigterm)
    
    await process_stream(redis, analyzer)
    await redis.close()
    logger.info("Worker stopped.")

if __name__ == "__main__":
    asyncio.run(main())
