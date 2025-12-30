from io import BytesIO

from elevenlabs import ElevenLabs

from ..config import settings


class TranscriptionError(Exception):
    pass


def transcribe(audio_bytes: bytes, filename: str = "audio.m4a") -> tuple[str, float | None]:
    """
    Transcribe audio bytes using ElevenLabs Speech-to-Text.

    Returns:
        tuple of (transcript_text, duration_seconds or None)
    """
    try:
        client = ElevenLabs(api_key=settings.elevenlabs_api_key)
        audio_file = BytesIO(audio_bytes)
        audio_file.name = filename

        result = client.speech_to_text.convert(
            file=audio_file,
            model_id="scribe_v1",
            language_code="eng",
        )

        text = result.text if hasattr(result, "text") else str(result)

        # ElevenLabs may return duration info - extract if available
        duration = None
        if hasattr(result, "audio_duration"):
            duration = result.audio_duration

        return text, duration

    except Exception as e:
        raise TranscriptionError(f"Transcription failed: {e}") from e
