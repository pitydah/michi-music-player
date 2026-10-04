"""Audio Phase 2 context tool (R11.1 §183, contract R11-G12-CONTEXT-TOOL).

Extracts bounded context packs for one phase from the single canonical R11.1
spec: bootstrap, the phase card and every declared MUST_READ_ANCHORS contract.
Section numbers are navigation only; anchors are the machine API.

One deviation from the literal reference implementation, documented here and
covered by tests: the canonical spec embeds its own anchor literals inside
code examples, so anchor uniqueness is evaluated on standalone anchor lines
(the same rule the repository alignment verifier uses) instead of a plain
substring count. Everything else follows the reference byte-for-byte.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

CANONICAL_NAME = "MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md"
CANONICAL_PATH = Path("docs/audio") / CANONICAL_NAME

PHASE_RE = re.compile(
    r"<!-- MICHI_PHASE2:PHASE:(AP2-F\d{2}):BEGIN -->(.*?)"
    r"<!-- MICHI_PHASE2:PHASE:\1:END -->",
    re.DOTALL,
)
CONTRACT_RE = re.compile(
    r"<!-- MICHI_PHASE2:CONTRACT:([A-Z0-9-]+):BEGIN -->(.*?)"
    r"<!-- MICHI_PHASE2:CONTRACT:\1:END -->",
    re.DOTALL,
)
TOP_SECTION_RE = re.compile(r"^# (\d+)\. ", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class PlanIndex:
    path: Path
    sha256: str
    text: str
    phase_blocks: dict[str, str]
    contracts: dict[str, str]


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_spec(repo: Path) -> Path:
    preferred = repo / CANONICAL_PATH
    if preferred.is_file():
        return preferred
    completed = subprocess.run(
        ["git", "-C", str(repo), "ls-files", f"*{CANONICAL_NAME}"],
        check=True,
        capture_output=True,
        text=True,
    )
    matches = [
        repo / line.strip() for line in completed.stdout.splitlines() if line.strip()
    ]
    if len(matches) != 1:
        raise SystemExit(
            "STOP_SPEC_NOT_FOUND" if not matches else "STOP_SPEC_AMBIGUOUS"
        )
    return matches[0]


def _unique_matches(regex: re.Pattern, text: str, kind: str) -> dict[str, str]:
    result: dict[str, str] = {}
    counts: dict[str, int] = {}
    for match in regex.finditer(text):
        key = match.group(1)
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > 1:
            raise SystemExit(f"STOP_{kind}_DUPLICATE:{key}")
        result[key] = match.group(2).strip()
    return result


def validate_unique_top_level_numbers(text: str) -> None:
    # R11 itself is normalized to unique top-level numeric headings.
    # Fail instead of silently overwriting if a future edit reintroduces one.
    found: dict[int, int] = {}
    for match in TOP_SECTION_RE.finditer(text):
        number = int(match.group(1))
        if number in found:
            raise SystemExit(f"STOP_SPEC_DUPLICATE_SECTION:{number}")
        found[number] = match.start()


def build_index(repo: Path) -> PlanIndex:
    path = resolve_spec(repo)
    data = path.read_bytes()
    text = data.decode("utf-8")
    validate_unique_top_level_numbers(text)
    phases = _unique_matches(PHASE_RE, text, "PHASE")
    contracts = _unique_matches(CONTRACT_RE, text, "CONTRACT")
    if not contracts:
        raise SystemExit("STOP_CONTRACT_INDEX_EMPTY")
    return PlanIndex(
        path=path,
        sha256=digest_bytes(data),
        text=text,
        phase_blocks=phases,
        contracts=contracts,
    )


def bounded_block(text: str, begin: str, end: str, code: str) -> str:
    """Extract one anchor-bounded block using standalone anchor lines.

    The canonical spec reproduces its own anchor literals inside code blocks;
    counting raw substrings would reject the real canonical document, so the
    uniqueness rule matches the alignment verifier: exactly one standalone
    BEGIN line and one standalone END line, in order.
    """
    begin_line = re.compile(rf"^{re.escape(begin)}$", re.MULTILINE)
    end_line = re.compile(rf"^{re.escape(end)}$", re.MULTILINE)
    start = begin_line.search(text)
    stop = end_line.search(text)
    if start is None or stop is None or start.end() > stop.start():
        raise SystemExit(code)
    return text[start.end() : stop.start()].strip()


def parse_csv_field(block: str, key: str) -> tuple[str, ...]:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", block, re.MULTILINE)
    if match is None:
        return ()
    return tuple(x.strip() for x in match.group(1).split(",") if x.strip())


def must_read_anchors(block: str) -> tuple[str, ...]:
    anchors = parse_csv_field(block, "MUST_READ_ANCHORS")
    if not anchors:
        raise SystemExit("STOP_PHASE_MUST_READ_ANCHORS_EMPTY")
    return anchors


def dependencies(block: str) -> tuple[str, ...]:
    return tuple(
        x for x in parse_csv_field(block, "DEPENDENCIES") if x.startswith("AP2-F")
    )


def emit_contract(index: PlanIndex, anchor: str) -> str:
    block = index.contracts.get(anchor)
    if block is None:
        raise SystemExit(f"STOP_CONTRACT_MISSING:{anchor}")
    return f"## CONTRACT {anchor}\n{block}"


def emit_context(index: PlanIndex, phase: str, mode: str) -> str:
    phase_block = index.phase_blocks.get(phase)
    if phase_block is None:
        raise SystemExit("STOP_PHASE_UNKNOWN")

    chunks = [
        "# PHASE2 R11 CONTEXT PACK",
        f"SPEC_PATH: {index.path}",
        f"SPEC_SHA256: {index.sha256}",
        "MODE: " + mode,
        "\n## BOOTSTRAP\n"
        + bounded_block(
            index.text,
            "<!-- MICHI_PHASE2:BOOTSTRAP:BEGIN -->",
            "<!-- MICHI_PHASE2:BOOTSTRAP:END -->",
            "STOP_SPEC_BOOTSTRAP_ANCHOR_INVALID",
        ),
        f"\n## PRIMARY PHASE {phase}\n{phase_block}",
    ]

    if mode == "orientation":
        chunks.append(
            "\n# ORIENTATION_ONLY\n"
            "PRODUCTIVE_MUTATION_ALLOWED: FALSE\n"
            "Run --mode implementation before editing."
        )
        return "\n\n".join(chunks)

    seen: set[str] = set()
    for anchor in must_read_anchors(phase_block):
        if anchor in seen:
            continue
        chunks.append("\n" + emit_contract(index, anchor))
        seen.add(anchor)

    if mode == "deep":
        for dep in dependencies(phase_block):
            dep_block = index.phase_blocks.get(dep)
            if dep_block is None:
                raise SystemExit(f"STOP_DEPENDENCY_PHASE_MISSING:{dep}")
            chunks.append(f"\n## DEPENDENCY PHASE {dep}\n{dep_block}")
            for anchor in must_read_anchors(dep_block):
                if anchor not in seen:
                    chunks.append("\n" + emit_contract(index, anchor))
                    seen.add(anchor)

    chunks.append("\nPRODUCTIVE_MUTATION_ALLOWED: TRUE")
    return "\n\n".join(chunks)


def receipt(index: PlanIndex, phase: str) -> dict[str, object]:
    block = index.phase_blocks.get(phase)
    if block is None:
        raise SystemExit("STOP_PHASE_UNKNOWN")
    anchors = must_read_anchors(block)
    for anchor in anchors:
        if anchor not in index.contracts:
            raise SystemExit(f"STOP_CONTRACT_MISSING:{anchor}")
    contract_material = "\n".join(
        f"{anchor}\n{index.contracts[anchor]}" for anchor in anchors
    ).encode()
    return {
        "spec_path": str(index.path),
        "spec_sha256": index.sha256,
        "primary_phase": phase,
        "dependencies": dependencies(block),
        "must_read_anchors": anchors,
        "contract_set_sha256": digest_bytes(contract_material),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="phase2_context")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--phase", required=True)
    parser.add_argument(
        "--mode",
        choices=("orientation", "implementation", "deep"),
        default="implementation",
    )
    parser.add_argument("--receipt-json", action="store_true")
    args = parser.parse_args(argv)

    index = build_index(Path(args.repo).resolve())
    if args.receipt_json:
        print(json.dumps(receipt(index, args.phase), indent=2))
        return 0
    print(emit_context(index, args.phase, args.mode))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
