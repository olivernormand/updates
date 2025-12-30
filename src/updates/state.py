from datetime import datetime, timedelta

from .schemas import Highlight, SubmissionRecord


# In-memory state
_submissions: list[SubmissionRecord] = []
_current_context: str | None = None
_context_set_at: datetime | None = None


def add_submission(
    transcript: str,
    highlight: Highlight,
    readwise_id: int | None = None,
) -> SubmissionRecord:
    record = SubmissionRecord(
        transcript=transcript,
        highlight=highlight,
        readwise_id=readwise_id,
        created_at=datetime.now(),
    )
    _submissions.append(record)
    return record


def get_recent(hours: int = 2, limit: int = 10) -> list[SubmissionRecord]:
    cutoff = datetime.now() - timedelta(hours=hours)
    recent = [s for s in _submissions if s.created_at >= cutoff]
    recent.sort(key=lambda s: s.created_at, reverse=True)
    return recent[:limit]


def format_recent_context(submissions: list[SubmissionRecord]) -> str:
    if not submissions:
        return ""
    lines = ["Recent updates:"]
    for s in submissions:
        title = s.highlight.title or "Unknown"
        text = s.highlight.text[:50] + "..." if len(s.highlight.text) > 50 else s.highlight.text
        time_str = s.created_at.strftime("%H:%M")
        lines.append(f"- [{title}] {text} ({time_str})")
    return "\n".join(lines)


def set_context(text: str) -> None:
    global _current_context, _context_set_at
    _current_context = text
    _context_set_at = datetime.now()


def get_context() -> tuple[str | None, datetime | None]:
    return _current_context, _context_set_at
