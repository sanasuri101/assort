from fastapi import APIRouter, Depends, Query
from typing import List, Optional
import redis.asyncio as redis
from app.config import settings
from pydantic import BaseModel
import json
import asyncio

router = APIRouter()

# --- Models ---
class DashboardStats(BaseModel):
    total_calls: int
    resolved_calls: int
    avg_duration_sec: float
    sentiment_score: float

class CallSummary(BaseModel):
    call_id: str
    started_at: str # ISO timestamp
    outcome: str
    duration_sec: int
    patient_name: Optional[str] = None
    summary: Optional[str] = None

class TranscriptSegment(BaseModel):
    role: str
    content: str
    timestamp: float
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[str] = None
    tool_result: Optional[str] = None

class CallDetail(CallSummary):
    transcript: List[TranscriptSegment]
    recording_url: Optional[str] = None

# --- Endpoints ---

@router.get("/stats", response_model=DashboardStats)
async def get_stats():
    # Real aggregation logic
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        keys = await r.keys("analysis:*")
        total = len(keys)
        resolved = 0
        durations = []
        sentiments = []
        
        for k in keys:
            data = await r.hgetall(k)
            if data.get("outcome") in ["scheduled", "answered"]:
                resolved += 1
            if "duration" in data:
                durations.append(float(data["duration"]))
            # Sentiment mapping: positive=1.0, neutral=0.5, negative=0.0
            sent = data.get("sentiment", "neutral")
            sentiments.append(1.0 if sent == "positive" else 0.5 if sent == "neutral" else 0.0)
            
        avg_dur = sum(durations) / len(durations) if durations else 0.0
        avg_sent = sum(sentiments) / len(sentiments) if sentiments else 0.0
        
        return DashboardStats(
            total_calls=total,
            resolved_calls=resolved,
            avg_duration_sec=avg_dur,
            sentiment_score=avg_sent
        )
    finally:
        await r.close()

@router.get("/calls", response_model=List[CallSummary])
async def get_calls(limit: int = 20):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # Scan for call metadata keys
        keys = await r.keys("call:*:metadata")
        # Support legacy keys or different key formats if needed
        if not keys:
            keys = await r.keys("call:*")
            # Filter out sub-keys like :transcript, :events
            keys = [k for k in keys if k.count(":") == 1]
            
        results = []
        for key in keys:
            call_id = key.split(":")[1]
            data = await r.hgetall(key)
            if data:
                # Try to find analysis
                analysis = await r.hgetall(f"analysis:{call_id}")
                results.append(CallSummary(
                    call_id=call_id,
                    started_at=data.get("created_at", "unknown"),
                    outcome=analysis.get("outcome", "in-progress"),
                    duration_sec=int(data.get("duration", 0)),
                    patient_name=data.get("patient_name", "Anonymous"),
                    summary=analysis.get("summary", "Analysis pending...")
                ))
        
        # Sort by timestamp desc (if possible)
        results.sort(key=lambda x: x.started_at, reverse=True)
        
        if not results:
             return []
             
        return results[:limit]
    finally:
        await r.close()

@router.get("/calls/{call_id}", response_model=CallDetail)
async def get_call_detail(call_id: str):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        data = await r.hgetall(f"call:{call_id}")
        analysis = await r.hgetall(f"analysis:{call_id}")
        
        # Fetch transcript list
        transcript_lines = await r.lrange(f"call:{call_id}:transcript", 0, -1)
        transcript = []
        for i, line in enumerate(transcript_lines):
            try:
                role, content = line.split(": ", 1)
                role = role.lower()
                segment = TranscriptSegment(role=role, content=content, timestamp=i*2.0)
                
                # Try to parse tool details if it's a tool role
                if role == "tool":
                    # Simple heuristic: "tool: name(args) -> result" or just "tool: name"
                    if "(" in content:
                        t_name, rest = content.split("(", 1)
                        segment.tool_name = t_name.strip()
                    else:
                        segment.tool_name = content.strip()
                
                transcript.append(segment)
            except:
                transcript.append(TranscriptSegment(role="unknown", content=line, timestamp=i*2.0))
        
        if not data and not transcript:
             raise HTTPException(status_code=404, detail="Call record not found")

        return CallDetail(
            call_id=call_id,
            started_at=data.get("created_at", "unknown"),
            outcome=analysis.get("outcome", "completed"),
            duration_sec=int(data.get("duration", 0)),
            patient_name=data.get("patient_name", "Anonymous"),
            summary=analysis.get("summary", ""),
            transcript=transcript
        )
    finally:
        await r.close()

# --- Knowledge Base endpoints ---

class KnowledgeItem(BaseModel):
    key: str
    content: str

@router.get("/knowledge", response_model=List[KnowledgeItem])
async def list_knowledge():
    r = redis.from_url(settings.redis_url, decode_responses=False) # bytes for embedding
    try:
        keys = await r.keys("knowledge:*")
        results = []
        for key in keys:
            data = await r.hgetall(key)
            if data:
                key_str = key.decode("utf-8").replace("knowledge:", "")
                content = data[b"content"].decode("utf-8")
                results.append(KnowledgeItem(key=key_str, content=content))
        return results
    finally:
        await r.close()

@router.post("/knowledge")
async def update_knowledge(item: KnowledgeItem):
    from app.voice.knowledge import KnowledgeBase
    kb = KnowledgeBase(settings.redis_url)
    try:
        await kb.seed({item.key: item.content})
        return {"status": "success"}
    finally:
        await kb.close()

@router.delete("/knowledge/{key}")
async def delete_knowledge(key: str):
    r = redis.from_url(settings.redis_url)
    try:
        await r.delete(f"knowledge:{key}")
        return {"status": "success"}
    finally:
        await r.close()

# --- Settings endpoints ---

class PracticeSettings(BaseModel):
    practice_name: str
    office_hours: str
    insurance_plans: List[str]

@router.get("/settings", response_model=PracticeSettings)
async def get_settings():
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        data = await r.hgetall("settings:practice")
        if not data:
            return PracticeSettings(
                practice_name=settings.practice_name,
                office_hours="Mon-Fri 8:00 AM - 5:00 PM",
                insurance_plans=["Aetna", "Blue Cross", "United Healthcare"]
            )
        return PracticeSettings(
            practice_name=data.get("practice_name", settings.practice_name),
            office_hours=data.get("office_hours", "Mon-Fri 8:00 AM - 5:00 PM"),
            insurance_plans=json.loads(data.get("insurance_plans", '["Aetna", "Blue Cross", "United Healthcare"]'))
        )
    finally:
        await r.close()

@router.post("/settings")
async def update_settings(s: PracticeSettings):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.hset("settings:practice", mapping={
            "practice_name": s.practice_name,
            "office_hours": s.office_hours,
            "insurance_plans": json.dumps(s.insurance_plans)
        })
        return {"status": "success"}
    finally:
        await r.close()

# --- Learning Loop endpoints ---

class LearningCandidate(BaseModel):
    id: str
    question: str
    answer: str
    confidence: float
    source_call_id: str

@router.get("/learning/candidates", response_model=List[LearningCandidate])
async def list_candidates():
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # Get all IDs from the list
        cand_ids = await r.lrange("candidates:knowledge", 0, -1)
        results = []
        for cid in cand_ids:
            data = await r.hgetall(cid)
            if data:
                data["id"] = cid
                results.append(LearningCandidate(**data))
        return results
    finally:
        await r.close()

@router.post("/learning/approve/{cand_id}")
async def approve_candidate(cand_id: str):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        data = await r.hgetall(cand_id)
        if not data:
            return {"status": "error", "message": "Candidate not found"}
        
        # Add to KB
        from app.voice.knowledge import KnowledgeBase
        kb = KnowledgeBase(settings.redis_url)
        try:
            # generating a key from the question or just the cand_id
            key = f"faq_{hash(data['question']) % 10000}"
            await kb.seed({key: data['answer']})
        finally:
            await kb.close()
        
        # Remove from candidates list and hash
        await r.lrem("candidates:knowledge", 0, cand_id)
        await r.delete(cand_id)
        
        return {"status": "success"}
    finally:
        await r.close()

@router.delete("/learning/reject/{cand_id}")
async def reject_candidate(cand_id: str):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.lrem("candidates:knowledge", 0, cand_id)
        await r.delete(cand_id)
        return {"status": "success"}
    finally:
        await r.close()

# --- Live Monitor endpoints ---

class LiveCall(BaseModel):
    call_id: str
    patient_name: Optional[str] = None
    status: str
    duration_sec: int

@router.get("/live", response_model=List[LiveCall])
async def get_live_calls():
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        # Scan for active calls
        # Scan for active calls
        active_keys = await r.keys("call:*:metadata")
        results = []
        for key in active_keys:
             # Check if analysis exists. If no analysis, it might be active
             call_id = key.split(":")[1]
             analysis_exists = await r.exists(f"analysis:{call_id}")
             if not analysis_exists:
                 meta = await r.hgetall(key)
                 results.append(LiveCall(
                     call_id=call_id,
                     patient_name=meta.get("patient_name", "Anonymous"),
                     status="in-progress",
                     duration_sec=0
                 ))
        
        # No mocks for live calls
            
        return results
    finally:
        await r.close()
