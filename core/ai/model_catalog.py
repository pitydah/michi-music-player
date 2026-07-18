from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ModelEntry:
    id: str
    name: str
    description: str
    base_model: str
    gguf_file: str
    size_mb: int
    ram_estimate_mb: int
    url: str
    sha256: str
    license: str
    min_ram_gb: int
    min_cpu_cores: int
    family: str
    parameters: str
    languages: list[str] = field(default_factory=lambda: ["es", "en"])


_CATALOG: list[ModelEntry] = [
    ModelEntry(
        id="munchkin",
        name="Michi Munchkin",
        description="Pequeño, rápido. Ideal para PCs básicos y laptops antiguas.",
        base_model="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        gguf_file="qwen2.5-0.5b-instruct-q4_k_m.gguf",
        size_mb=350,
        ram_estimate_mb=500,
        url="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf",
        sha256="",
        license="Apache 2.0",
        min_ram_gb=1,
        min_cpu_cores=2,
        family="qwen",
        parameters="0.5B",
    ),
    ModelEntry(
        id="carey",
        name="Michi Carey",
        description="Equilibrado. Buen rendimiento en PCs de gama media.",
        base_model="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        gguf_file="qwen2.5-1.5b-instruct-q4_k_m.gguf",
        size_mb=1000,
        ram_estimate_mb=1500,
        url="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        sha256="",
        license="Apache 2.0",
        min_ram_gb=2,
        min_cpu_cores=4,
        family="qwen",
        parameters="1.5B",
    ),
    ModelEntry(
        id="maine_coon",
        name="Michi Maine Coon",
        description="El más grande y capaz. Ideal para PCs potentes y estaciones de trabajo.",
        base_model="LMFlow/LFM-3B",
        gguf_file="lfm-3b-q4_k_m.gguf",
        size_mb=2000,
        ram_estimate_mb=3000,
        url="",
        sha256="",
        license="Apache 2.0",
        min_ram_gb=4,
        min_cpu_cores=6,
        family="lfm",
        parameters="3B",
    ),
]


def get_catalog() -> list[ModelEntry]:
    return list(_CATALOG)


def get_entry(model_id: str) -> ModelEntry | None:
    for entry in _CATALOG:
        if entry.id == model_id:
            return entry
    return None


def get_entry_by_family(family: str) -> list[ModelEntry]:
    return [e for e in _CATALOG if e.family == family]
