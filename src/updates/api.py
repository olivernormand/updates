from fastapi import FastAPI, File, HTTPException, UploadFile

from . import state
from .schemas import (
    ContextRequest,
    ContextResponse,
    HealthResponse,
    Highlight,
    ParseRequest,
    ProcessResponse,
    RecentResponse,
    SubmitRequest,
    SubmitResponse,
    TranscribeResponse,
)
from .services import claude, elevenlabs, readwise
from .services.claude import ParsingError
from .services.elevenlabs import TranscriptionError
from .services.readwise import ReadwiseError

app = FastAPI(
    title="Updates API",
    description="Voice-to-Readwise capture tool",
    version="0.1.0",
)


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio file to text using ElevenLabs."""
    try:
        audio_bytes = await audio.read()
        text, duration = elevenlabs.transcribe(audio_bytes, audio.filename or "audio.m4a")
        return TranscribeResponse(text=text, duration_seconds=duration)
    except TranscriptionError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse", response_model=Highlight)
async def parse_transcript(request: ParseRequest):
    """Parse transcript into structured Readwise highlight."""
    try:
        context = None
        if request.include_recent_context:
            current, _ = state.get_context()
            recent = state.get_recent()
            context = {
                "current": current,
                "recent": [
                    {"title": s.highlight.title, "text": s.highlight.text[:100]}
                    for s in recent
                ],
            }

        return claude.parse(request.text, context)
    except ParsingError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submit", response_model=SubmitResponse)
async def submit_to_readwise(request: SubmitRequest):
    """Submit a highlight to Readwise."""
    try:
        highlight = Highlight(
            text=request.text,
            title=request.title,
            author=request.author,
            category=request.category,
            note=request.note,
            location=request.location,
            location_type=request.location_type,
        )
        readwise_id = await readwise.submit_highlight(highlight)
        return SubmitResponse(success=True, readwise_id=readwise_id)
    except ReadwiseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process", response_model=ProcessResponse)
async def process_audio(audio: UploadFile = File(...)):
    """Full pipeline: transcribe -> parse -> submit."""
    try:
        # Step 1: Transcribe
        audio_bytes = await audio.read()
        transcript, _ = elevenlabs.transcribe(audio_bytes, audio.filename or "audio.m4a")

        # Step 2: Parse
        current, _ = state.get_context()
        recent = state.get_recent()
        context = {
            "current": current,
            "recent": [
                {"title": s.highlight.title, "text": s.highlight.text[:100]}
                for s in recent
            ],
        }
        highlight = claude.parse(transcript, context)

        # Step 3: Submit to Readwise
        readwise_id = await readwise.submit_highlight(highlight)

        # Step 4: Record submission
        state.add_submission(transcript, highlight, readwise_id)

        return ProcessResponse(
            success=True,
            transcript=transcript,
            highlight=highlight,
            readwise_id=readwise_id,
        )

    except TranscriptionError as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    except ParsingError as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {e}")
    except ReadwiseError as e:
        raise HTTPException(status_code=500, detail=f"Readwise submission failed: {e}")


@app.get("/context", response_model=ContextResponse)
async def get_context():
    """Get current reading/listening context."""
    context, set_at = state.get_context()
    return ContextResponse(context=context, set_at=set_at)


@app.put("/context")
async def set_context(request: ContextRequest):
    """Set current reading/listening context."""
    state.set_context(request.context)
    return {"success": True}


@app.get("/recent", response_model=RecentResponse)
async def get_recent():
    """Get recent submissions (last 2 hours)."""
    recent = state.get_recent()
    context_string = state.format_recent_context(recent)
    return RecentResponse(
        count=len(recent),
        context_string=context_string,
        highlights=recent,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service connectivity."""
    readwise_ok = await readwise.check_connection()

    return HealthResponse(
        status="ok" if readwise_ok else "degraded",
        services={
            "elevenlabs": True,  # Can't easily check without making a request
            "anthropic": True,  # Can't easily check without making a request
            "readwise": readwise_ok,
        },
    )


def run():
    """Run the API server."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run()
