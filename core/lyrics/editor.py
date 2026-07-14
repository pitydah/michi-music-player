from __future__ import annotations

import copy
from typing import Callable

from core.lyrics.models import (
    LyricsDocument, LyricsLine, LyricsOperationResult,
    LyricsErrorCode,
)


class LyricsEditorService:
    def __init__(self, clock: Callable[[], str] | None = None):
        self._clock = clock or (lambda: __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()))
        self._undo_stack: list[LyricsDocument] = []
        self._redo_stack: list[LyricsDocument] = []
        self._max_history = 50
        self._dirty = False
        self._current: LyricsDocument | None = None

    def load(self, doc: LyricsDocument):
        self._current = copy.deepcopy(doc)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._dirty = False

    @property
    def current(self) -> LyricsDocument | None:
        return self._current

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    def replace_plain_text(self, text: str) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        self._push_undo()
        self._current.plain_text = text
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def replace_synced_text(self, text: str) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        self._push_undo()
        from core.lyrics.parser import parse_lrc
        parsed = parse_lrc(text)
        self._current.lines = parsed.lines
        self._current.synced_text = text
        self._current.metadata = parsed.metadata
        self._current.offset_ms = parsed.offset_ms
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def shift_all(self, offset_ms: int) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        self._push_undo()
        for line in self._current.lines:
            line.start_ms = max(0, line.start_ms + offset_ms)
            if line.end_ms > 0:
                line.end_ms = max(0, line.end_ms + offset_ms)
            for word in line.words:
                word.start_ms = max(0, word.start_ms + offset_ms)
                word.end_ms = max(0, word.end_ms + offset_ms)
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def shift_range(self, start_idx: int, end_idx: int, offset_ms: int) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        self._push_undo()
        for line in self._current.lines[start_idx:end_idx + 1]:
            line.start_ms = max(0, line.start_ms + offset_ms)
            if line.end_ms > 0:
                line.end_ms = max(0, line.end_ms + offset_ms)
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def set_line_timestamp(self, line_id: str, start_ms: float, end_ms: float = 0.0) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        if start_ms < 0 or end_ms < 0:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR, message="Negative timestamps not allowed")
        self._push_undo()
        for line in self._current.lines:
            if line.line_id == line_id:
                line.start_ms = start_ms
                if end_ms > 0:
                    line.end_ms = end_ms
                self._dirty = True
                return LyricsOperationResult(ok=True, document=self._current)
        return LyricsOperationResult(ok=False, code=LyricsErrorCode.NOT_FOUND, message=f"Line {line_id} not found")

    def insert_line(self, after_idx: int, text: str, start_ms: float = 0.0) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        self._push_undo()
        line = LyricsLine(
            line_id=str(len(self._current.lines)),
            start_ms=start_ms,
            text=text,
        )
        self._current.lines.insert(after_idx + 1, line)
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def delete_line(self, line_id: str) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        self._push_undo()
        self._current.lines = [ln for ln in self._current.lines if ln.line_id != line_id]
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def split_line(self, line_id: str, position: int) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        for i, line in enumerate(self._current.lines):
            if line.line_id == line_id:
                if position <= 0 or position >= len(line.text):
                    return LyricsOperationResult(ok=False, message="Invalid split position")
                self._push_undo()
                front = line.text[:position]
                back = line.text[position:]
                line.text = front
                new_line = LyricsLine(
                    line_id=str(len(self._current.lines)),
                    start_ms=line.start_ms,
                    text=back,
                )
                self._current.lines.insert(i + 1, new_line)
                self._dirty = True
                return LyricsOperationResult(ok=True, document=self._current)
        return LyricsOperationResult(ok=False, code=LyricsErrorCode.NOT_FOUND)

    def merge_lines(self, first_id: str, second_id: str) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        first = None
        second = None
        for line in self._current.lines:
            if line.line_id == first_id:
                first = line
            if line.line_id == second_id:
                second = line
        if first is None or second is None:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.NOT_FOUND)
        self._push_undo()
        first.text = first.text + " " + second.text
        self._current.lines = [ln for ln in self._current.lines if ln.line_id != second_id]
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def normalize_timestamps(self) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        self._push_undo()
        self._current.lines.sort(key=lambda ln: ln.start_ms)
        for i in range(len(self._current.lines) - 1):
            if self._current.lines[i].end_ms <= 0 or self._current.lines[i].end_ms > self._current.lines[i + 1].start_ms:
                self._current.lines[i].end_ms = self._current.lines[i + 1].start_ms
        if self._current.lines and self._current.lines[-1].end_ms <= 0:
            self._current.lines[-1].end_ms = self._current.lines[-1].start_ms + 5000
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def clear_timestamps(self) -> LyricsOperationResult:
        if not self._current:
            return LyricsOperationResult(ok=False, code=LyricsErrorCode.INTERNAL_ERROR)
        self._push_undo()
        for line in self._current.lines:
            line.start_ms = 0.0
            line.end_ms = 0.0
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def undo(self) -> LyricsOperationResult:
        if not self._undo_stack:
            return LyricsOperationResult(ok=False, message="Nothing to undo")
        if self._current:
            self._redo_stack.append(copy.deepcopy(self._current))
        self._current = self._undo_stack.pop()
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def redo(self) -> LyricsOperationResult:
        if not self._redo_stack:
            return LyricsOperationResult(ok=False, message="Nothing to redo")
        if self._current:
            self._undo_stack.append(copy.deepcopy(self._current))
        self._current = self._redo_stack.pop()
        self._dirty = True
        return LyricsOperationResult(ok=True, document=self._current)

    def validate(self) -> list[str]:
        warnings: list[str] = []
        if not self._current:
            return ["No document loaded"]
        for i, line in enumerate(self._current.lines):
            if line.start_ms < 0:
                warnings.append(f"Line {i}: negative start_ms")
            if line.end_ms < 0:
                warnings.append(f"Line {i}: negative end_ms")
            if line.end_ms > 0 and line.end_ms < line.start_ms:
                warnings.append(f"Line {i}: end_ms before start_ms")
        for i in range(len(self._current.lines) - 1):
            if self._current.lines[i].start_ms > self._current.lines[i + 1].start_ms:
                warnings.append(f"Lines {i}/{i+1}: unsorted timestamps")
        return warnings

    def _push_undo(self):
        if self._current:
            self._undo_stack.append(copy.deepcopy(self._current))
            if len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)
            self._redo_stack.clear()
