import httpx

from ..config import settings
from ..schemas import Highlight


class ReadwiseError(Exception):
    pass


async def submit_highlight(highlight: Highlight) -> int:
    """
    Submit a highlight to Readwise.

    Returns:
        The Readwise highlight ID

    Raises:
        ReadwiseError: If title is missing or submission fails
    """
    if not highlight.title:
        raise ReadwiseError("Title is required for Readwise submission")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            highlight_data = {
                "text": highlight.text,
                "title": highlight.title,
                "source_type": "updates_app",
            }

            if highlight.author:
                highlight_data["author"] = highlight.author
            if highlight.category:
                highlight_data["category"] = highlight.category.value
            if highlight.note:
                highlight_data["note"] = highlight.note
            if highlight.location is not None:
                highlight_data["location"] = highlight.location
            if highlight.location_type:
                highlight_data["location_type"] = highlight.location_type.value

            response = await client.post(
                "https://readwise.io/api/v2/highlights/",
                headers={"Authorization": f"Token {settings.readwise_access_token}"},
                json={"highlights": [highlight_data]},
            )

            response.raise_for_status()
            data = response.json()

            # Readwise returns the created highlights
            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get("id", 0)

            return 0

    except httpx.HTTPStatusError as e:
        raise ReadwiseError(f"Readwise API error: {e.response.status_code}") from e
    except Exception as e:
        raise ReadwiseError(f"Failed to submit to Readwise: {e}") from e


async def check_connection() -> bool:
    """Check if Readwise API is accessible."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://readwise.io/api/v2/auth/",
                headers={"Authorization": f"Token {settings.readwise_access_token}"},
            )
            return response.status_code == 204
    except Exception:
        return False
