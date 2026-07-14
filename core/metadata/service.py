from __future__ import annotations

import logging
from typing import Callable

from core.metadata.models import (
    MetadataDocument, MetadataFieldChange,
    MetadataOperationResult, JournalEntry,
)
from core.metadata.enums import (
    MetadataErrorCode, BackupPolicy, BatchPolicy,
    JournalStatus,
)
from core.metadata.reader import MetadataReader
from core.metadata.writer import MetadataWriter
from core.metadata.registry import MetadataFormatRegistry
from core.metadata.normalizer import MetadataNormalizer
from core.metadata.backup_rollback import MetadataBackupService, MetadataRollbackService
from core.metadata.journal import MetadataJournalRepository
from core.metadata.cancellation import MetadataCancellationToken

logger = logging.getLogger("michi.metadata.service")


class MetadataService:
    def __init__(
        self,
        registry: MetadataFormatRegistry | None = None,
        reader: MetadataReader | None = None,
        writer: MetadataWriter | None = None,
        normalizer: MetadataNormalizer | None = None,
        backup_service: MetadataBackupService | None = None,
        rollback_service: MetadataRollbackService | None = None,
        journal_repo: MetadataJournalRepository | None = None,
        clock: Callable[[], str] | None = None,
    ):
        self._registry = registry or MetadataFormatRegistry.default_registry()
        self._reader = reader or MetadataReader(self._registry)
        self._writer = writer or MetadataWriter(self._registry)
        self._normalizer = normalizer or MetadataNormalizer()
        self._backup = backup_service or MetadataBackupService()
        self._rollback = rollback_service or MetadataRollbackService(self._backup)
        self._journal = journal_repo
        self._clock = clock or (lambda: __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()))

    def probe(self, path: str) -> MetadataOperationResult:
        return self._reader.probe(path)

    def read(self, path: str, include_artwork_metadata: bool = True,
             include_artwork_bytes: bool = False,
             include_raw_fields: bool = False) -> MetadataOperationResult:
        return self._reader.read(path, include_artwork_metadata,
                                 include_artwork_bytes, include_raw_fields)

    def read_many(self, paths: list[str], include_artwork_metadata: bool = True,
                  token: MetadataCancellationToken | None = None) -> list[MetadataOperationResult]:
        results = []
        for path in paths:
            if token and token.cancelled:
                results.append(MetadataOperationResult(
                    ok=False, code=MetadataErrorCode.CANCELLED.value,
                ))
                break
            results.append(self.read(path, include_artwork_metadata))
        return results

    def normalize(self, doc: MetadataDocument) -> MetadataDocument:
        return self._normalizer.normalize_document(doc)

    def write(self, path: str, doc: MetadataDocument,
              changes: list[MetadataFieldChange] | None = None,
              backup_policy: BackupPolicy | None = None) -> MetadataOperationResult:
        result = self._writer.write(path, doc, changes, backup_policy)
        if self._journal:
            self._journal_create(path, result)
        return result

    def create_backup(self, path: str,
                      policy: BackupPolicy = BackupPolicy.FULL_FILE_BACKUP) -> MetadataOperationResult:
        return self._backup.create_backup(path, policy)

    def rollback(self, original_path: str, backup_path: str,
                 before_signature: str) -> MetadataOperationResult:
        return self._rollback.rollback(original_path, backup_path, before_signature)

    def batch_apply(self, targets: list[tuple[str, MetadataDocument, list[MetadataFieldChange]]],
                    policy: BatchPolicy = BatchPolicy.STOP_ON_FIRST_FAILURE,
                    token: MetadataCancellationToken | None = None) -> list[MetadataOperationResult]:
        self._next_id()
        results: list[MetadataOperationResult] = []

        for i, (path, doc, changes) in enumerate(targets):
            if token and token.cancelled:
                results.append(MetadataOperationResult(
                    ok=False, code=MetadataErrorCode.CANCELLED.value,
                    message=f"Cancelled at {i}/{len(targets)}",
                ))
                break
            result = self.write(path, doc, changes)
            results.append(result)
            if not result.ok and policy == BatchPolicy.STOP_ON_FIRST_FAILURE:
                break
            if not result.ok and policy == BatchPolicy.ALL_OR_NOTHING:
                for j in range(len(results) - 1):
                    prev = results[j]
                    if prev.ok and prev.data.get("backup_path"):
                        self._rollback.rollback(
                            targets[j][0],
                            prev.data["backup_path"],
                            prev.data.get("before_signature", ""),
                        )
                break

        return results

    def lookup_by_mbid(self, mbid: str) -> MetadataOperationResult:
        try:
            from integrations.musicbrainz.provider import MusicBrainzProvider
            mb = MusicBrainzProvider()
            return mb.lookup_recording(mbid)
        except ImportError:
            return MetadataOperationResult(
                ok=False, code=MetadataErrorCode.DEPENDENCY_UNAVAILABLE.value,
                message="MusicBrainz provider not available",
            )

    def health(self) -> dict:
        return {
            "formats": len(self._registry.all()),
            "readable": len(self._registry.list_readable()),
            "writable": len(self._registry.list_writable()),
        }

    def shutdown(self):
        if self._journal:
            self._journal = None

    def _journal_create(self, path: str, result: MetadataOperationResult):
        if not self._journal:
            return
        entry = JournalEntry(
            operation_id=self._next_id(),
            target=path,
            status=JournalStatus.COMPLETED if result.ok else JournalStatus.FAILED,
            before_signature=result.data.get("before_signature", ""),
            after_signature=result.data.get("after_signature", ""),
            backup_reference=result.data.get("backup_path", ""),
            started_at=self._clock(),
            completed_at=self._clock(),
            result_code=result.code,
        )
        self._journal.create(entry)

    @staticmethod
    def _next_id() -> str:
        import uuid
        return str(uuid.uuid4())[:8]



