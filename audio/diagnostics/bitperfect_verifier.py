"""Bit-Perfect Verifier — compares input format against actual ALSA output.

Reads /proc/asound/*/hw_params when available to verify that the DAC is
receiving the exact same signal as the source file, with no DSP in between.
"""

import logging

from audio.diagnostics.alsa_hw_params import find_active_hw_params
from audio.diagnostics.bitperfect_report import BitperfectReport
from audio.output_profiles import AudioOutputProfile
from audio.format_probe import AudioFormatInfo

logger = logging.getLogger("michi.bitperfect")


def verify_bitperfect(
    input_format: AudioFormatInfo,
    profile: AudioOutputProfile,
    diagnostics,
) -> BitperfectReport:
    """Verify bit-perfect status for current playback.

    Args:
        input_format: probed format of the current file
        profile: active audio output profile
        diagnostics: AudioDiagnostics or AudioRouteDiagnostics with
                     device_string, eq_active, replaygain_active, etc.

    Returns:
        BitperfectReport with status and reasons.
    """
    report = BitperfectReport(
        requested=profile.bitperfect,
        possible=False,
        device=getattr(diagnostics, 'device_string', ''),
    )

    if not profile.bitperfect:
        report.status = "off"
        return report

    report.input_sample_rate = input_format.sample_rate
    report.input_bit_depth = input_format.bit_depth
    report.input_channels = input_format.channels
    report.possible = True

    # Check for DSP that breaks bit-perfect
    has_eq = getattr(diagnostics, 'eq_active', False)
    has_replaygain = getattr(diagnostics, 'replaygain_active', False)
    has_spectrum = getattr(diagnostics, 'spectrum_active', False)
    has_resampling = getattr(diagnostics, 'resampling_active', False)

    if has_eq:
        report.reasons.append("EQ activo — rompe bit-perfect")
    if has_replaygain:
        report.reasons.append("ReplayGain activo — rompe bit-perfect")
    if has_spectrum:
        report.reasons.append("Spectrum activo — rompe bit-perfect")
    if has_resampling:
        report.reasons.append("Resampling activo — rompe bit-perfect")

    device_str = getattr(diagnostics, 'device_string', '')
    if device_str and "plughw" in device_str:
        report.reasons.append("Dispositivo plughw — posible conversión en ALSA")
    if device_str and "autoaudiosink" in device_str:
        report.reasons.append("Salida por defecto del sistema — no es ALSA hw directo")
    if device_str and "pipewire" in device_str.lower():
        report.reasons.append("PipeWire activo — posible modificación de la señal")
    if device_str and "pulse" in device_str.lower():
        report.reasons.append("PulseAudio activo — posible modificación de la señal")

    # Try to read actual ALSA hw_params
    active = find_active_hw_params()
    matching = _find_matching_device(active, device_str)

    if not active:
        if report.reasons:
            report.status = "broken"
            report.reasons.append("No se pudo leer hw_params de ALSA")
        else:
            report.status = "not_verified"
            report.reasons.append("No se pudo leer hw_params de ALSA — no se puede verificar")
        return report

    if matching:
        report.output_sample_rate = matching.sample_rate
        report.output_format = matching.format
        report.output_channels = matching.channels
    else:
        if active:
            report.output_sample_rate = active[0].sample_rate
            report.output_format = active[0].format

    # Compare input vs output
    if matching:
        _check_rate_match(report, input_format, matching)
        _check_format_match(report, input_format, matching)
        _check_channels_match(report, input_format, matching)
    else:
        if active:
            report.status = "not_verified"
            report.reasons.append("Dispositivo ALSA activo no coincide con el esperado")
            return report

    if report.reasons:
        report.status = "broken"
    else:
        report.status = "verified"
        report.verified = True

    return report


def _find_matching_device(
    active: list, device_str: str
):
    """Find active hw_params that match the expected ALSA device.

    Supports formats: hw:X,Y, hw:CARD=X,DEV=Y, alsa:hw:X,Y
    """
    import re
    m = re.search(r"(?:alsa:)?hw:(\d+|CARD=(\d+)),(\d+|DEV=(\d+))", device_str)
    if not m:
        m = re.search(r"hw:(\d+),(\d+)", device_str)
        if not m:
            return None
        target_card = int(m.group(1))
        target_dev = int(m.group(2))
    else:
        target_card = int(m.group(2) or m.group(1))
        target_dev = int(m.group(4) or m.group(3))
    for params in active:
        if params.card == target_card and params.device == target_dev:
            return params
    return None


def _check_rate_match(
    report: BitperfectReport,
    input_fmt: AudioFormatInfo,
    hw_params,
):
    if (
        input_fmt.sample_rate > 0
        and hw_params.sample_rate > 0
        and input_fmt.sample_rate != hw_params.sample_rate
    ):
        report.reasons.append(
            f"Resampling: archivo {input_fmt.sample_rate} Hz, "
            f"DAC recibe {hw_params.sample_rate} Hz"
        )


_FORMAT_DEPTH_MAP = {
    "S16_LE": 16,
    "S24_LE": 24,
    "S24_3LE": 24,
    "S32_LE": 32,
    "S8": 8,
    "U8": 8,
    "FLOAT": 32,
    "FLOAT64": 64,
    "DSD_U8": 8,
    "IEC958_SUBFRAME_LE": 32,
}


def _check_channels_match(
    report: BitperfectReport,
    input_fmt: AudioFormatInfo,
    hw_params,
):
    if (
        input_fmt.channels > 0
        and hw_params.channels > 0
        and input_fmt.channels != hw_params.channels
    ):
        report.reasons.append(
            f"Canales distintos: archivo {input_fmt.channels}, "
            f"DAC recibe {hw_params.channels}"
        )


def _check_format_match(
    report: BitperfectReport,
    input_fmt: AudioFormatInfo,
    hw_params,
):
    if input_fmt.bit_depth > 0 and hw_params.format:
        output_depth = _FORMAT_DEPTH_MAP.get(hw_params.format, 0)
        if output_depth and input_fmt.bit_depth != output_depth:
            report.reasons.append(
                f"Conversión de formato: archivo {input_fmt.bit_depth}-bit, "
                f"DAC recibe {output_depth}-bit ({hw_params.format})"
            )
