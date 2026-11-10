"""Official firmware repository consumer (R6): GitHub Releases ONLY.

- Versioned, immutable releases — never ``main``, raw files or ephemeral CI
  artifacts.
- Asset naming is CONFIGURABLE while STREAM-REQ-004 remains open (the default
  convention is the one requested from Stream tooling).
- Integrity: every asset must publish a ``sha256`` digest (GitHub API); a
  missing digest fails closed. HTTPS alone is NOT authenticity: ``materialize``
  requires a ``ManifestAuthenticityVerifierPort``.
- Flow: resolve release → verify manifest (hash + authenticity + board) →
  download bundle (hash) → safe extraction → verify every segment → atomic
  publish into the cache.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Callable

from michi_ecosystem.domain.firmware import (
    FirmwareChannel,
    FirmwareProvenance,
    FirmwareRelease,
    ResolvedFirmware,
)
from michi_ecosystem.infrastructure.flashing.firmware_cache import (
    FirmwareCache,
    sha256_file,
)
from michi_ecosystem.infrastructure.flashing.http_client import (
    HttpClientPort,
    HttpError,
)
from michi_ecosystem.infrastructure.flashing.manifest_verifier import (
    ManifestError,
    load_manifest,
    verify_artifact,
)
from michi_ecosystem.infrastructure.flashing.safe_extract import (
    ExtractionError,
    safe_extract_zip,
)
from michi_ecosystem.ports.firmware_repository import (
    ManifestAuthenticityVerifierPort,
)

OFFICIAL_REPOSITORY = "pitydah/michi-music-stream"
DEFAULT_API_BASE = "https://api.github.com"
# Requested upstream convention (STREAM-REQ-004); configurable until frozen.
DEFAULT_MANIFEST_PATTERN = "factory-manifest-{board}.json"
DEFAULT_BUNDLE_PATTERN = "factory-bundle-{board}.zip"


class FirmwareRepositoryError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class GitHubReleaseFirmwareRepository:
    def __init__(
        self,
        *,
        http: HttpClientPort,
        cache: FirmwareCache,
        authenticity: ManifestAuthenticityVerifierPort | None = None,
        repository: str = OFFICIAL_REPOSITORY,
        api_base: str = DEFAULT_API_BASE,
        manifest_pattern: str = DEFAULT_MANIFEST_PATTERN,
        bundle_pattern: str = DEFAULT_BUNDLE_PATTERN,
    ) -> None:
        self._http = http
        self._cache = cache
        self._authenticity = authenticity
        self._repository = repository
        self._api_base = api_base
        self._manifest_pattern = manifest_pattern
        self._bundle_pattern = bundle_pattern

    # ── resolution ──────────────────────────────────────────────────────

    def recommended(
        self, board: str, channel: str = "stable"
    ) -> FirmwareRelease | None:
        wanted_prerelease = channel == "dev"
        manifest_name = self._manifest_pattern.format(board=board)
        bundle_name = self._bundle_pattern.format(board=board)
        for release in self._list_releases():
            if release.get("draft"):
                continue
            if bool(release.get("prerelease")) != wanted_prerelease:
                continue
            assets = {
                str(asset.get("name")): asset
                for asset in release.get("assets", [])
                if isinstance(asset, dict)
            }
            if manifest_name not in assets or bundle_name not in assets:
                continue
            tag = str(release.get("tag_name", "")).strip()
            if not tag:
                continue
            return FirmwareRelease(
                version=tag.lstrip("v"),
                tag=tag,
                board=board,
                channel=(
                    FirmwareChannel.DEV if wanted_prerelease else FirmwareChannel.STABLE
                ),
                manifest_asset=manifest_name,
                bundle_asset=bundle_name,
            )
        return None

    # ── materialization ─────────────────────────────────────────────────

    def materialize(
        self,
        release: FirmwareRelease,
        *,
        progress: Callable[[int, int | None], None] | None = None,
    ) -> ResolvedFirmware:
        if self._authenticity is None:
            raise FirmwareRepositoryError(
                "AUTHENTICITY_NOT_CONFIGURED",
                "sin verificador de autenticidad; el flasheo no puede proceder",
            )
        assets = self._release_assets(release)
        manifest_asset = self._require_asset(assets, release.manifest_asset)
        bundle_asset = self._require_asset(assets, release.bundle_asset)
        manifest_sha = self._digest(manifest_asset)
        bundle_sha = self._digest(bundle_asset)
        source_commit = release.source_commit or self._resolve_source_commit(
            release.tag
        )
        provenance = FirmwareProvenance(
            repository=self._repository,
            release_tag=release.tag,
            source_commit=source_commit,
            manifest_sha256=manifest_sha,
            bundle_sha256=bundle_sha,
        )

        target = self._cache.release_dir(release)
        cached_manifest_path = target / release.manifest_asset
        if cached_manifest_path.is_file():
            cached = None
            cached_bytes = b""
            try:
                cached_bytes = cached_manifest_path.read_bytes()
                cached = load_manifest(cached_manifest_path)
            except (OSError, ManifestError):
                cached = None
            if cached is not None and cached.board == release.board:
                # Cache is NEVER authority: the cached manifest must match the
                # release asset digest AND pass authenticity again.
                digest_ok = hashlib.sha256(cached_bytes).hexdigest() == manifest_sha
                authentic_ok = digest_ok and self._authenticity.verify(
                    cached_bytes, provenance=provenance
                )
                if authentic_ok and self._cache.is_verified(release, cached):
                    return ResolvedFirmware(
                        release=release,
                        manifest=cached,
                        artifacts_dir=target / "artifacts",
                        provenance=provenance,
                    )
            self._cache.purge(release)

        staging = target.with_name(target.name + ".staging")
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        try:
            manifest_bytes = self._download_bytes(manifest_asset, max_bytes=1024 * 1024)
            if hashlib.sha256(manifest_bytes).hexdigest() != manifest_sha:
                raise FirmwareRepositoryError(
                    "ARTIFACT_HASH_MISMATCH", "hash del manifest no coincide"
                )
            manifest_path = staging / release.manifest_asset
            manifest_path.write_bytes(manifest_bytes)
            try:
                manifest = load_manifest(manifest_path)
            except ManifestError as exc:
                raise FirmwareRepositoryError("MANIFEST_INVALID", str(exc)) from exc
            if manifest.board != release.board:
                raise FirmwareRepositoryError(
                    "BOARD_MISMATCH",
                    f"manifest para {manifest.board}, release para {release.board}",
                )
            if manifest.product and manifest.product != "michi-music-stream":
                raise FirmwareRepositoryError(
                    "PRODUCT_MISMATCH",
                    f"product inesperado: {manifest.product}",
                )
            if manifest.chip_target and manifest.chip_target != "esp32s3":
                raise FirmwareRepositoryError(
                    "CHIP_MISMATCH",
                    f"chip target inesperado: {manifest.chip_target}",
                )
            if manifest.release_tag and manifest.release_tag != release.tag:
                raise FirmwareRepositoryError(
                    "RELEASE_TAG_MISMATCH",
                    f"manifest declara {manifest.release_tag}, "
                    f"release es {release.tag}",
                )
            if (
                manifest.source_commit
                and manifest.source_commit != provenance.source_commit
            ):
                raise FirmwareRepositoryError(
                    "SOURCE_COMMIT_MISMATCH",
                    "el commit del manifest no coincide con el de la release",
                )
            if manifest.flash_size is not None:
                highest = 0
                for segment in manifest.segments:
                    if segment.size:
                        highest = max(highest, segment.offset + segment.size)
                descriptor = manifest.factory_partition
                if descriptor is not None:
                    highest = max(highest, descriptor.offset + descriptor.capacity)
                if highest > manifest.flash_size:
                    raise FirmwareRepositoryError(
                        "FLASH_SIZE_EXCEEDED",
                        "un segmento excede el flash_size declarado",
                    )
            if not self._authenticity.verify(manifest_bytes, provenance=provenance):
                raise FirmwareRepositoryError(
                    "MANIFEST_UNAUTHENTIC", "autenticidad del manifest no verificada"
                )

            bundle_path = staging / release.bundle_asset
            url = str(bundle_asset.get("browser_download_url", ""))
            try:
                self._http.download(url, bundle_path, progress=progress)
            except HttpError as exc:
                raise FirmwareRepositoryError("DOWNLOAD_FAILED", str(exc)) from exc
            if sha256_file(bundle_path) != bundle_sha:
                raise FirmwareRepositoryError(
                    "ARTIFACT_HASH_MISMATCH", "hash del bundle no coincide"
                )

            artifacts = staging / "artifacts"
            try:
                safe_extract_zip(bundle_path, artifacts)
            except ExtractionError as exc:
                raise FirmwareRepositoryError("EXTRACTION_REJECTED", str(exc)) from exc
            for segment in manifest.segments:
                try:
                    verify_artifact(manifest, segment, artifacts)
                except ManifestError as exc:
                    raise FirmwareRepositoryError(
                        "ARTIFACT_HASH_MISMATCH", str(exc)
                    ) from exc

            if target.exists():
                self._cache.purge(release)
            staging.rename(target)
            return ResolvedFirmware(
                release=release,
                manifest=manifest,
                artifacts_dir=target / "artifacts",
                provenance=provenance,
            )
        except FirmwareRepositoryError:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    # ── internals ───────────────────────────────────────────────────────

    def _resolve_source_commit(self, tag: str) -> str:
        """Resolve the release tag to its source commit (fail closed)."""
        url = f"{self._api_base}/repos/{self._repository}/git/ref/tags/{tag}"
        try:
            ref = self._http.get_json(url)
        except HttpError as exc:
            raise FirmwareRepositoryError("GITHUB_UNAVAILABLE", str(exc)) from exc
        obj = ref.get("object") if isinstance(ref, dict) else None
        if not isinstance(obj, dict):
            raise FirmwareRepositoryError(
                "RELEASE_PROVENANCE_INCOMPLETE",
                f"no se pudo resolver el commit de {tag}",
            )
        sha = str(obj.get("sha", ""))
        if obj.get("type") == "tag":
            detail_url = f"{self._api_base}/repos/{self._repository}/git/tags/{sha}"
            try:
                detail = self._http.get_json(detail_url)
            except HttpError as exc:
                raise FirmwareRepositoryError("GITHUB_UNAVAILABLE", str(exc)) from exc
            nested = detail.get("object") if isinstance(detail, dict) else None
            sha = str(nested.get("sha", "")) if isinstance(nested, dict) else ""
        if len(sha) != 40:
            raise FirmwareRepositoryError(
                "RELEASE_PROVENANCE_INCOMPLETE",
                f"commit inválido para {tag}",
            )
        return sha.lower()

    def _list_releases(self) -> list[dict]:
        url = f"{self._api_base}/repos/{self._repository}/releases?per_page=30"
        try:
            payload = self._http.get_json(url)
        except HttpError as exc:
            raise FirmwareRepositoryError("GITHUB_UNAVAILABLE", str(exc)) from exc
        if not isinstance(payload, list):
            raise FirmwareRepositoryError(
                "GITHUB_MALFORMED", "respuesta de releases inesperada"
            )
        return [item for item in payload if isinstance(item, dict)]

    def _release_assets(self, release: FirmwareRelease) -> dict[str, dict]:
        url = f"{self._api_base}/repos/{self._repository}/releases/tags/{release.tag}"
        try:
            payload = self._http.get_json(url)
        except HttpError as exc:
            raise FirmwareRepositoryError("GITHUB_UNAVAILABLE", str(exc)) from exc
        if not isinstance(payload, dict):
            raise FirmwareRepositoryError(
                "GITHUB_MALFORMED", "respuesta de release inesperada"
            )
        return {
            str(asset.get("name")): asset
            for asset in payload.get("assets", [])
            if isinstance(asset, dict)
        }

    @staticmethod
    def _require_asset(assets: dict[str, dict], name: str) -> dict:
        try:
            return assets[name]
        except KeyError as exc:
            raise FirmwareRepositoryError(
                "ASSET_MISSING", f"release sin asset {name!r}"
            ) from exc

    @staticmethod
    def _digest(asset: dict) -> str:
        digest = asset.get("digest")
        if (
            not isinstance(digest, str)
            or not digest.startswith("sha256:")
            or len(digest) != len("sha256:") + 64
        ):
            raise FirmwareRepositoryError(
                "ASSET_DIGEST_MISSING",
                f"el asset {asset.get('name')!r} no publica digest sha256",
            )
        return digest.split(":", 1)[1].lower()

    def _download_bytes(self, asset: dict, *, max_bytes: int) -> bytes:
        url = str(asset.get("browser_download_url", ""))
        try:
            return self._http.get_bytes(url, max_bytes=max_bytes)
        except HttpError as exc:
            raise FirmwareRepositoryError("DOWNLOAD_FAILED", str(exc)) from exc
