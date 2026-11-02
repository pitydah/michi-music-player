"""Compatibility re-export of the canonical pure RBJ biquad math.

The implementation now lives in ``michi.domain.biquad`` so application and
presentation layers can consume the SAME coefficients without importing the
infrastructure layer.
"""

from michi.domain.biquad import (
    BiquadCoefficients,
    biquad_coefficients,
    biquad_magnitude_db,
)

__all__ = ["BiquadCoefficients", "biquad_coefficients", "biquad_magnitude_db"]
