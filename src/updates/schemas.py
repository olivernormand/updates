from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class Category(str, Enum):
    books = "books"
    articles = "articles"
    podcasts = "podcasts"
    tweets = "tweets"


class LocationType(str, Enum):
    page = "page"
    order = "order"
    time_offset = "time_offset"


# Request models
class ParseRequest(BaseModel):
    text: str
    include_recent_context: bool = True


class SubmitRequest(BaseModel):
    text: str
    title: str | None = None
    author: str | None = None
    category: Category | None = None
    note: str | None = None
    location: int | None = None
    location_type: LocationType | None = None


class ContextRequest(BaseModel):
    context: str


# Response models
class TranscribeResponse(BaseModel):
    text: str
    duration_seconds: float | None = None


class Highlight(BaseModel):
    text: str
    title: str | None = None
    author: str | None = None
    category: Category | None = None
    note: str | None = None
    location: int | None = None
    location_type: LocationType | None = None


class SubmitResponse(BaseModel):
    success: bool
    readwise_id: int | None = None


class ProcessResponse(BaseModel):
    success: bool
    transcript: str
    highlight: Highlight
    readwise_id: int | None = None


class ContextResponse(BaseModel):
    context: str | None
    set_at: datetime | None


class SubmissionRecord(BaseModel):
    transcript: str
    highlight: Highlight
    readwise_id: int | None
    created_at: datetime


class RecentResponse(BaseModel):
    count: int
    context_string: str
    highlights: list[SubmissionRecord]


class HealthResponse(BaseModel):
    status: str
    services: dict[str, bool]
