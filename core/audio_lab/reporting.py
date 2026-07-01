"""Report Center — exportación unificada de reportes para Audio Lab.

Reutiliza generate_report() de diagnostics_service para reportes de diagnóstico.
Agrega formatos TXT, CSV, JSON genéricos.
"""

from __future__ import annotations

import csv
import io
import json


def format_txt(report: dict, title: str = "Reporte") -> str:
    lines = [f"=== {title} ==="]
    _dict_to_lines(report, lines, indent=0)
    return "\n".join(lines)


def format_csv(report: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    _dict_to_csv(report, w)
    return buf.getvalue()


def format_json(report: dict, indent: int = 2) -> str:
    return json.dumps(report, indent=indent, ensure_ascii=False, default=str)


def health_to_txt(health: dict) -> str:
    lines = [
        "=== Salud de la biblioteca ===",
        f"Total archivos: {health.get('total_tracks', 0)}",
        f"Analizados: {health.get('analysed_tracks', 0)}",
        f"Pendientes: {health.get('pending_analysis', 0)}",
        f"Errores: {health.get('error_analysis', 0)}",
        f"Hi-Res: {health.get('hires_count', 0)}",
        f"Lossless: {health.get('lossless_count', 0)}",
        f"Lossy: {health.get('lossy_count', 0)}",
        f"DSD: {health.get('dsd_count', 0)}",
        f"Advertencias espectrales: {health.get('spectral_warnings', 0)}",
        f"Metadatos incompletos: {health.get('missing_metadata', 0)}",
        f"Tamaño total: {health.get('total_size_mb', 0)} MB",
        f"Duración total: {health.get('total_duration_str', '')}",
    ]
    return "\n".join(lines)


def health_to_json(health: dict) -> str:
    return json.dumps(health, indent=2, ensure_ascii=False, default=str)


def _dict_to_lines(d, lines, indent=0):
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}{k}:")
            _dict_to_lines(v, lines, indent + 1)
        elif isinstance(v, list):
            lines.append(f"{prefix}{k}: {len(v)} elemento(s)")
        else:
            lines.append(f"{prefix}{k}: {v}")


def _dict_to_csv(d, writer, parent_key=""):
    for k, v in d.items():
        key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            _dict_to_csv(v, writer, key)
        elif isinstance(v, list):
            writer.writerow([key, len(v)])
        else:
            writer.writerow([key, v])
