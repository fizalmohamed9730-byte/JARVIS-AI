"""Pydantic V2 schemas for all API request / response models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Enums ────────────────────────────────────────────────────────────────

class MessageRoleEnum(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class TaskPriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskStatusEnum(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class RepeatTypeEnum(str, Enum):
    none = "none"
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


# ── Auth / User ──────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, examples=["jarvis_user"])
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["StrongP@ssw0rd"])
    full_name: Optional[str] = Field(None, max_length=128, examples=["Tony Stark"])


class UserLogin(BaseModel):
    email: EmailStr = Field(..., examples=["user@example.com"])
    password: str = Field(..., examples=["StrongP@ssw0rd"])


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_path: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


# ── Conversation ─────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: str = Field("New Conversation", max_length=255, examples=["Research session"])
    summary: Optional[str] = Field(None, examples=["Discussion about AI ethics"])


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ConversationList(BaseModel):
    items: List[ConversationResponse]
    total: int
    page: int
    page_size: int


# ── Message ──────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    role: MessageRoleEnum = Field(..., description="Role of the message sender")
    content: str = Field(..., min_length=1, max_length=100000, examples=["Hello JARVIS"])


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: MessageRoleEnum
    content: str
    tokens_used: Optional[int] = None
    model_used: Optional[str] = None
    created_at: datetime


# ── Task ─────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, examples=["Buy groceries"])
    description: Optional[str] = Field(None, examples=["Milk, eggs, bread"])
    priority: TaskPriorityEnum = Field(TaskPriorityEnum.medium)
    due_date: Optional[datetime] = Field(None, examples=["2026-07-20T18:00:00Z"])
    reminder_at: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    priority: Optional[TaskPriorityEnum] = None
    status: Optional[TaskStatusEnum] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    priority: TaskPriorityEnum
    status: TaskStatusEnum
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


# ── Note ─────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, examples=["Meeting notes"])
    content: str = Field("", examples=["Discussed the roadmap for Q3"])
    tags: List[str] = Field(default_factory=list, examples=[["meeting", "roadmap"]])
    category: Optional[str] = Field(None, max_length=64, examples=["work"])
    is_pinned: bool = Field(False)


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    is_pinned: Optional[bool] = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    content: str
    tags: Optional[List[str]] = None
    category: Optional[str] = None
    is_pinned: bool
    created_at: datetime
    updated_at: datetime


# ── Reminder ─────────────────────────────────────────────────────────────

class ReminderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, examples=["Call dentist"])
    message: Optional[str] = Field(None, examples=["Annual checkup"])
    trigger_at: datetime = Field(..., examples=["2026-07-20T09:00:00Z"])
    repeat_type: RepeatTypeEnum = Field(RepeatTypeEnum.none)


class ReminderUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    message: Optional[str] = None
    trigger_at: Optional[datetime] = None
    repeat_type: Optional[RepeatTypeEnum] = None
    is_completed: Optional[bool] = None


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    message: Optional[str] = None
    trigger_at: datetime
    repeat_type: RepeatTypeEnum
    is_completed: bool
    created_at: datetime


# ── Email ────────────────────────────────────────────────────────────────

class EmailAccountCreate(BaseModel):
    email: EmailStr
    imap_server: str = Field("imap.gmail.com", max_length=255)
    smtp_server: str = Field("smtp.gmail.com", max_length=255)
    password: str = Field(..., min_length=1, max_length=512)


class EmailAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email: str
    imap_server: str
    smtp_server: str
    is_active: bool


class EmailSend(BaseModel):
    to: List[EmailStr] = Field(..., min_length=1, examples=[["colleague@example.com"]])
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    subject: str = Field(..., min_length=1, max_length=998, examples=["Project update"])
    body: str = Field(..., min_length=1, examples=["Here is the latest status..."])
    html: bool = Field(False, description="Send as HTML email")
    account_id: Optional[int] = Field(None, description="Email account to send from")


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    subject: str
    sender: str
    recipients: List[str]
    date: datetime
    body: str
    is_read: bool = False
    has_attachments: bool = False


# ── Calendar ─────────────────────────────────────────────────────────────

class CalendarEventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, examples=["Team standup"])
    description: Optional[str] = Field(None, examples=["Weekly sync"])
    start_time: datetime = Field(..., examples=["2026-07-20T09:00:00Z"])
    end_time: datetime = Field(..., examples=["2026-07-20T09:30:00Z"])
    location: Optional[str] = Field(None, max_length=512, examples=["Conference Room A"])
    attendees: List[str] = Field(default_factory=list, examples=[["alice@example.com"]])
    recurrence: Optional[str] = Field(None, examples=["RRULE:FREQ=WEEKLY;BYDAY=MO"])


class CalendarEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    recurrence: Optional[str] = None
    google_event_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ── Memory ───────────────────────────────────────────────────────────────

class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000, examples=["User prefers dark mode"])
    category: Optional[str] = Field(None, max_length=64, examples=["preference"])
    metadata: Optional[Dict[str, Any]] = Field(None, examples=[{"source": "voice"}])
    expires_at: Optional[datetime] = None


class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    content: str
    category: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding_id: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None


# ── Search ───────────────────────────────────────────────────────────────

class SearchQuery(BaseModel):
    q: str = Field(..., min_length=1, max_length=500, examples=["machine learning notes"])
    category: Optional[str] = Field(None, examples=["notes"])
    limit: int = Field(10, ge=1, le=100)


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str


# ── Voice ────────────────────────────────────────────────────────────────

class VoiceCommand(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, examples=["What's on my calendar today?"])
    language: str = Field("en-US", max_length=10)
    context: Optional[Dict[str, Any]] = None


class VoiceResponse(BaseModel):
    text: str
    action: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    audio_path: Optional[str] = None


# ── Automation ───────────────────────────────────────────────────────────

class AutomationCommand(BaseModel):
    command: str = Field(..., min_length=1, max_length=1000, examples=["open chrome"])
    parameters: Optional[Dict[str, Any]] = Field(None, examples=[{"url": "https://google.com"}])


class AutomationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ── Settings ─────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    wake_word: Optional[str] = None
    voice_language: Optional[str] = None
    energy_threshold: Optional[int] = Field(None, ge=0, le=10000)
    openai_model: Optional[str] = None
    ollama_model: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


# ── Health ───────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    timestamp: datetime


class DetailedHealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    database: str
    redis: str
    ai_services: Dict[str, str]
