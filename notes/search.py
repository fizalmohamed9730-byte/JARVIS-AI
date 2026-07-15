"""Notes search engine for JARVIS AI assistant."""

import re
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass, field

from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with relevance information."""
    note_id: str
    title: str
    score: float
    highlights: Dict[str, List[str]] = field(default_factory=dict)
    snippet: str = ""


class NotesSearch:
    """Advanced search engine for notes."""

    def __init__(self):
        self._index: Dict[str, Dict[str, float]] = {}
        self._documents: Dict[str, dict] = {}

    def build_index(self, notes: List[dict]) -> None:
        """Build search index from notes."""
        self._index.clear()
        self._documents.clear()

        for note in notes:
            note_id = note["id"]
            self._documents[note_id] = note

            tokens = self._tokenize(
                f"{note.get('title', '')} {note.get('content', '')} "
                f"{' '.join(note.get('tags', []))} {note.get('category', '')}"
            )

            term_freq: Dict[str, float] = {}
            for token in tokens:
                term_freq[token] = term_freq.get(token, 0) + 1

            if tokens:
                for token, freq in term_freq.items():
                    term_freq[token] = freq / len(tokens)

            self._index[note_id] = term_freq

        logger.info(f"Search index built with {len(self._index)} documents")

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text for search indexing."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if len(t) > 1]

    def full_text_search(
        self,
        query: str,
        notes: Optional[List[dict]] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """Perform full-text search."""
        if notes:
            self.build_index(notes)

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[str, float] = {}
        highlights: Dict[str, List[str]] = {}

        for note_id, term_freq in self._index.items():
            score = 0.0
            note_highlights = []

            for token in query_tokens:
                if token in term_freq:
                    score += term_freq[token]

                for term, freq in term_freq.items():
                    similarity = SequenceMatcher(None, token, term).ratio()
                    if similarity > 0.8:
                        score += freq * similarity * 0.5

            if score > 0:
                note = self._documents.get(note_id, {})
                title = note.get("title", "")
                content = note.get("content", "")

                for token in query_tokens:
                    title_matches = re.findall(
                        rf'\b\w*{re.escape(token)}\w*\b',
                        title.lower()
                    )
                    content_matches = re.findall(
                        rf'.{{0,50}}\b\w*{re.escape(token)}\w*\b.{{0,50}}',
                        content.lower()
                    )
                    note_highlights.extend(title_matches)
                    note_highlights.extend(content_matches[:3])

                scores[note_id] = score
                highlights[note_id] = note_highlights

        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []

        for note_id, score in sorted_results[:limit]:
            note = self._documents.get(note_id, {})
            snippet = self._generate_snippet(
                note.get("content", ""),
                highlights.get(note_id, [])
            )

            results.append(SearchResult(
                note_id=note_id,
                title=note.get("title", ""),
                score=score,
                highlights={"matches": highlights.get(note_id, [])},
                snippet=snippet
            ))

        return results

    def _generate_snippet(self, content: str, matches: List[str], length: int = 200) -> str:
        """Generate a snippet around matched content."""
        if not matches:
            return content[:length] + "..." if len(content) > length else content

        first_match = matches[0]
        idx = content.lower().find(first_match.lower())

        if idx == -1:
            return content[:length] + "..." if len(content) > length else content

        start = max(0, idx - length // 2)
        end = min(len(content), idx + length // 2)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def tag_search(
        self,
        tags: List[str],
        notes: Optional[List[dict]] = None,
        match_all: bool = False
    ) -> List[SearchResult]:
        """Search notes by tags."""
        if notes:
            for note in notes:
                self._documents[note["id"]] = note

        results = []

        for note_id, note in self._documents.items():
            note_tags = set(t.lower() for t in note.get("tags", []))
            search_tags = set(t.lower() for t in tags)

            if match_all:
                matching = search_tags.issubset(note_tags)
            else:
                matching = bool(search_tags & note_tags)

            if matching:
                score = len(search_tags & note_tags) / max(len(search_tags), 1)
                results.append(SearchResult(
                    note_id=note_id,
                    title=note.get("title", ""),
                    score=score,
                    snippet=note.get("content", "")[:200]
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def date_range_search(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        notes: Optional[List[dict]] = None,
        date_field: str = "created_at"
    ) -> List[SearchResult]:
        """Search notes by date range."""
        if notes:
            for note in notes:
                self._documents[note["id"]] = note

        results = []

        for note_id, note in self._documents.items():
            date_str = note.get(date_field, "")
            if not date_str:
                continue

            try:
                note_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue

            if start_date:
                try:
                    start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    if note_date < start:
                        continue
                except ValueError:
                    continue

            if end_date:
                try:
                    end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                    if note_date > end:
                        continue
                except ValueError:
                    continue

            days_ago = (datetime.utcnow() - note_date.replace(tzinfo=None)).days
            score = max(0.1, 1.0 - (days_ago / 365.0))

            results.append(SearchResult(
                note_id=note_id,
                title=note.get("title", ""),
                score=score,
                snippet=note.get("content", "")[:200]
            ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def fuzzy_search(
        self,
        query: str,
        notes: Optional[List[dict]] = None,
        threshold: float = 0.6,
        limit: int = 20
    ) -> List[SearchResult]:
        """Perform fuzzy search with tolerance for typos."""
        if notes:
            for note in notes:
                self._documents[note["id"]] = note

        results = []
        query_lower = query.lower()

        for note_id, note in self._documents.items():
            title = note.get("title", "").lower()
            content = note.get("content", "").lower()
            tags = [t.lower() for t in note.get("tags", [])]

            title_score = SequenceMatcher(None, query_lower, title).ratio()
            tag_scores = [SequenceMatcher(None, query_lower, tag).ratio() for tag in tags]
            max_tag_score = max(tag_scores) if tag_scores else 0

            words = content.split()
            content_scores = []
            query_words = query_lower.split()
            for q_word in query_words:
                word_scores = [
                    SequenceMatcher(None, q_word, word).ratio()
                    for word in words
                ]
                if word_scores:
                    content_scores.append(max(word_scores))

            content_score = sum(content_scores) / max(len(content_scores), 1)

            best_score = max(title_score, max_tag_score, content_score)

            if best_score >= threshold:
                results.append(SearchResult(
                    note_id=note_id,
                    title=note.get("title", ""),
                    score=best_score,
                    snippet=content[:200]
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def highlight_matches(self, text: str, query: str) -> str:
        """Highlight matching text with markers."""
        query_tokens = self._tokenize(query)
        highlighted = text

        for token in query_tokens:
            pattern = re.compile(re.escape(token), re.IGNORECASE)
            highlighted = pattern.sub(f"**{token.upper()}**", highlighted)

        return highlighted

    def combined_search(
        self,
        query: str,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        notes: Optional[List[dict]] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """Combined search with multiple criteria."""
        if notes:
            for note in notes:
                self._documents[note["id"]] = note

        text_results = self.full_text_search(query, limit=limit * 2)
        text_scores = {r.note_id: r.score for r in text_results}

        tag_results = self.tag_search(tags) if tags else []
        tag_scores = {r.note_id: r.score for r in tag_results}

        date_results = self.date_range_search(start_date, end_date)
        date_scores = {r.note_id: r.score for r in date_results}

        all_note_ids = set(text_scores.keys()) | set(tag_scores.keys()) | set(date_scores.keys())

        combined_scores = []
        for note_id in all_note_ids:
            note = self._documents.get(note_id, {})

            if category and note.get("category", "").lower() != category.lower():
                continue

            text_score = text_scores.get(note_id, 0)
            tag_score = tag_scores.get(note_id, 0)
            date_score = date_scores.get(note_id, 0)

            combined = (
                text_score * 0.5 +
                tag_score * 0.3 +
                date_score * 0.2
            )

            combined_scores.append((note_id, combined))

        combined_scores.sort(key=lambda x: x[1], reverse=True)

        results = []
        for note_id, score in combined_scores[:limit]:
            note = self._documents.get(note_id, {})
            snippet = note.get("content", "")[:200]
            results.append(SearchResult(
                note_id=note_id,
                title=note.get("title", ""),
                score=score,
                snippet=snippet
            ))

        return results
