import anthropic
from pydantic import BaseModel

from ..config import settings
from ..schemas import Category, Highlight, LocationType


class ParsingError(Exception):
    pass


class ParsedHighlight(BaseModel):
    """Structured output model for Claude parsing - simplified to avoid anyOf complexity."""

    text: str
    title: str = ""
    author: str = ""
    category: str = "books"  # Will be: books, articles, podcasts
    note: str = ""
    location: int = 0  # 0 means not specified
    location_type: str = ""  # Will be: page, order, time_offset, or empty


SYSTEM_PROMPT = """You are a parser that converts voice transcripts into structured highlight data. Your primary job is to PRESERVE the user's exact words while extracting metadata.

CRITICAL: Do NOT rewrite or paraphrase the user's insight. Keep their exact wording. Only:
- Add proper punctuation (periods, commas, quotes)
- Fix obvious transcription errors (e.g., "their" vs "there")
- Remove only the source prefix (e.g., "update from thinking fast and slow" becomes the source, rest is the text)

Given:
1. A transcript of spoken audio
2. Optional context (current book/podcast, recent highlights)

Extract:
- text: The user's insight with their EXACT WORDING, just properly punctuated
- title: Source title (book, podcast, or article name)
- author: Author if mentioned or inferrable from your knowledge
- category: One of: books, articles, podcasts
- note: Personal commentary if present (phrases like "this reminds me of...", "I think...", "interesting because..."). Keep in the user's voice.
- location: Page number or timestamp if mentioned (as integer)
- location_type: One of: page, order, time_offset

Rules:
1. PRESERVE THE USER'S WORDS. Do not summarise, paraphrase, or "improve" their phrasing. The user wants to record their wording as they said it.
2. Strip source prefixes: "update from X", "from X", "in X" → extract as title, remove from text
3. If no source mentioned, use context (current book/podcast) if available
4. Add punctuation to make it readable, but don't change the words
5. If you recognise the book/podcast, add the author even if not stated
6. Separate personal notes from the core insight when present"""


def parse(transcript: str, context: dict | None = None) -> Highlight:
    """
    Parse a transcript into a structured highlight using Claude.

    Args:
        transcript: The raw transcript text
        context: Optional dict with 'current' (str) and 'recent' (list) keys

    Returns:
        Highlight with extracted metadata
    """
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        context_str = ""
        if context:
            if context.get("current"):
                context_str += f"\nCurrent context: {context['current']}"
            if context.get("recent"):
                context_str += "\nRecent highlights:"
                for r in context["recent"]:
                    context_str += f"\n- [{r.get('title', 'Unknown')}] {r.get('text', '')[:100]}"

        user_content = f"Transcript: {transcript}"
        if context_str:
            user_content += f"\n\nContext:{context_str}"

        response = client.beta.messages.parse(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            betas=["structured-outputs-2025-11-13"],
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
            output_format=ParsedHighlight,
        )

        parsed = response.parsed_output

        # Convert string values back to proper types, treating empty strings as None
        category = None
        if parsed.category and parsed.category in ("books", "articles", "podcasts", "tweets"):
            category = Category(parsed.category)

        location_type = None
        if parsed.location_type and parsed.location_type in ("page", "order", "time_offset"):
            location_type = LocationType(parsed.location_type)

        return Highlight(
            text=parsed.text,
            title=parsed.title if parsed.title else None,
            author=parsed.author if parsed.author else None,
            category=category,
            note=parsed.note if parsed.note else None,
            location=parsed.location if parsed.location > 0 else None,
            location_type=location_type,
        )

    except Exception as e:
        raise ParsingError(f"Parsing failed: {e}") from e
