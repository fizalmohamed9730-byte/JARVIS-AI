"""Notes manager for JARVIS AI assistant."""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class NoteFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    TXT = "txt"
    HTML = "html"


@dataclass
class Note:
    """Represents a single note."""
    id: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    created_at: str = ""
    updated_at: str = ""
    is_pinned: bool = False
    is_archived: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        """Convert note to dictionary."""
        return asdict(self)


class NotesManager:
    """Manages notes storage and operations."""

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "data/notes")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._notes: Dict[str, Note] = {}
        self._load_notes()

    def _load_notes(self) -> None:
        """Load notes from storage."""
        notes_file = self.storage_path / "notes.json"
        if notes_file.exists():
            try:
                with open(notes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for note_data in data:
                    note = Note(**note_data)
                    self._notes[note.id] = note
                logger.info(f"Loaded {len(self._notes)} notes")
            except Exception as e:
                logger.error(f"Failed to load notes: {e}")

    def _save_notes(self) -> None:
        """Save notes to storage."""
        notes_file = self.storage_path / "notes.json"
        try:
            data = [note.to_dict() for note in self._notes.values()]
            with open(notes_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save notes: {e}")

    def create_note(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        category: str = "general"
    ) -> Note:
        """Create a new note."""
        note_id = str(uuid.uuid4())
        note = Note(
            id=note_id,
            title=title,
            content=content,
            tags=tags or [],
            category=category
        )
        self._notes[note_id] = note
        self._save_notes()
        logger.info(f"Created note: {note_id}")
        return note

    def get_note(self, note_id: str) -> Optional[Note]:
        """Get note by ID."""
        return self._notes.get(note_id)

    def update_note(self, note_id: str, updates: Dict[str, Any]) -> Optional[Note]:
        """Update a note with new values."""
        note = self._notes.get(note_id)
        if not note:
            logger.warning(f"Note not found: {note_id}")
            return None

        for key, value in updates.items():
            if hasattr(note, key) and key not in ("id", "created_at"):
                setattr(note, key, value)

        note.updated_at = datetime.utcnow().isoformat()
        self._save_notes()
        logger.info(f"Updated note: {note_id}")
        return note

    def delete_note(self, note_id: str) -> bool:
        """Delete a note by ID."""
        if note_id in self._notes:
            del self._notes[note_id]
            self._save_notes()
            logger.info(f"Deleted note: {note_id}")
            return True
        logger.warning(f"Note not found for deletion: {note_id}")
        return False

    def search_notes(self, query: str) -> List[Note]:
        """Search notes by query string."""
        query_lower = query.lower()
        results = []

        for note in self._notes.values():
            score = 0

            if query_lower in note.title.lower():
                score += 10

            if query_lower in note.content.lower():
                score += 5

            for tag in note.tags:
                if query_lower in tag.lower():
                    score += 3

            if query_lower in note.category.lower():
                score += 2

            if score > 0:
                results.append((score, note))

        results.sort(key=lambda x: x[0], reverse=True)
        return [note for _, note in results]

    def get_notes(
        self,
        category: Optional[str] = None,
        pinned_only: bool = False,
        archived: bool = False
    ) -> List[Note]:
        """Get notes filtered by criteria."""
        notes = list(self._notes.values())

        if not archived:
            notes = [n for n in notes if not n.is_archived]

        if pinned_only:
            notes = [n for n in notes if n.is_pinned]

        if category:
            notes = [n for n in notes if n.category == category]

        notes.sort(
            key=lambda n: (n.is_pinned, n.updated_at),
            reverse=True
        )

        return notes

    def pin_note(self, note_id: str) -> bool:
        """Pin a note."""
        note = self._notes.get(note_id)
        if note:
            note.is_pinned = True
            note.updated_at = datetime.utcnow().isoformat()
            self._save_notes()
            return True
        return False

    def unpin_note(self, note_id: str) -> bool:
        """Unpin a note."""
        note = self._notes.get(note_id)
        if note:
            note.is_pinned = False
            note.updated_at = datetime.utcnow().isoformat()
            self._save_notes()
            return True
        return False

    def add_tags(self, note_id: str, tags: List[str]) -> bool:
        """Add tags to a note."""
        note = self._notes.get(note_id)
        if note:
            for tag in tags:
                if tag not in note.tags:
                    note.tags.append(tag)
            note.updated_at = datetime.utcnow().isoformat()
            self._save_notes()
            return True
        return False

    def remove_tags(self, note_id: str, tags: List[str]) -> bool:
        """Remove tags from a note."""
        note = self._notes.get(note_id)
        if note:
            note.tags = [t for t in note.tags if t not in tags]
            note.updated_at = datetime.utcnow().isoformat()
            self._save_notes()
            return True
        return False

    def export_note(self, note_id: str, format: NoteFormat = NoteFormat.MARKDOWN) -> str:
        """Export note in specified format."""
        note = self._notes.get(note_id)
        if not note:
            raise ValueError(f"Note not found: {note_id}")

        if format == NoteFormat.JSON:
            return json.dumps(note.to_dict(), indent=2, ensure_ascii=False)

        elif format == NoteFormat.MARKDOWN:
            lines = [
                f"# {note.title}",
                "",
                f"**Category:** {note.category}",
                f"**Tags:** {', '.join(note.tags) if note.tags else 'None'}",
                f"**Created:** {note.created_at}",
                f"**Updated:** {note.updated_at}",
                f"**Pinned:** {'Yes' if note.is_pinned else 'No'}",
                "",
                "---",
                "",
                note.content
            ]
            return "\n".join(lines)

        elif format == NoteFormat.TXT:
            lines = [
                note.title,
                "=" * len(note.title),
                "",
                f"Category: {note.category}",
                f"Tags: {', '.join(note.tags) if note.tags else 'None'}",
                f"Created: {note.created_at}",
                f"Updated: {note.updated_at}",
                "",
                note.content
            ]
            return "\n".join(lines)

        elif format == NoteFormat.HTML:
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{note.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; }}
        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
        .tag {{ background: #e0e0e0; padding: 2px 8px; border-radius: 4px; margin-right: 5px; }}
        .content {{ line-height: 1.6; }}
    </style>
</head>
<body>
    <h1>{note.title}</h1>
    <div class="meta">
        <p>Category: {note.category}</p>
        <p>Tags: {''.join(f'<span class="tag">{t}</span>' for t in note.tags)}</p>
        <p>Created: {note.created_at}</p>
        <p>Updated: {note.updated_at}</p>
    </div>
    <div class="content">
        <pre>{note.content}</pre>
    </div>
</body>
</html>"""
            return html

        raise ValueError(f"Unsupported format: {format}")

    def import_note(
        self,
        file_path: str,
        title: Optional[str] = None
    ) -> Note:
        """Import note from file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        note_title = title or path.stem

        if path.suffix == ".json":
            try:
                data = json.loads(content)
                note = Note(
                    id=str(uuid.uuid4()),
                    title=data.get("title", note_title),
                    content=data.get("content", content),
                    tags=data.get("tags", []),
                    category=data.get("category", "imported")
                )
            except json.JSONDecodeError:
                note = Note(
                    id=str(uuid.uuid4()),
                    title=note_title,
                    content=content,
                    category="imported"
                )
        else:
            note = Note(
                id=str(uuid.uuid4()),
                title=note_title,
                content=content,
                category="imported"
            )

        self._notes[note.id] = note
        self._save_notes()
        logger.info(f"Imported note: {note.id} from {file_path}")
        return note

    def archive_note(self, note_id: str) -> bool:
        """Archive a note."""
        note = self._notes.get(note_id)
        if note:
            note.is_archived = True
            note.updated_at = datetime.utcnow().isoformat()
            self._save_notes()
            return True
        return False

    def unarchive_note(self, note_id: str) -> bool:
        """Unarchive a note."""
        note = self._notes.get(note_id)
        if note:
            note.is_archived = False
            note.updated_at = datetime.utcnow().isoformat()
            self._save_notes()
            return True
        return False

    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        categories = set(note.category for note in self._notes.values())
        return sorted(categories)

    def get_all_tags(self) -> List[str]:
        """Get all unique tags."""
        tags = set()
        for note in self._notes.values():
            tags.update(note.tags)
        return sorted(tags)

    def get_stats(self) -> Dict[str, Any]:
        """Get notes statistics."""
        notes = list(self._notes.values())
        return {
            "total": len(notes),
            "pinned": sum(1 for n in notes if n.is_pinned),
            "archived": sum(1 for n in notes if n.is_archived),
            "categories": len(self.get_categories()),
            "tags": len(self.get_all_tags())
        }
