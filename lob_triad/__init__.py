"""lob_triad: Zero-Weight Level-3 Limit Order Book & Microstructure Tomography Spoke.

Features:
- Allocation-free #![no_std] Rust SIMD L3 tick book core (< 1.5 MB static arena).
- Discrete continuity TemporalClockContentSplitter (H_clock + H_nope) isolating quote flicker.
- Non-Local Causal Factorization (G_act vs Omega_reg) stripping high-frequency spoofing.
- 3-point discrete Morse impulse gate with 1-sample causal deferral (glint_rejected vs step_maneuver).
- so(C) skew-symmetric triad tie-breaker with 0.000e+00 spherical norm drift.
- Single-file WebGL2 L3 order-book reconstruction studio.
"""

__version__ = "0.1.0"

from lob_triad.arena import RustLOBEngine, is_rust_available
from lob_triad.core import (
    PurePythonLOBEngine,
    ACTION_ADD,
    ACTION_CANCEL,
    ACTION_REPLACE,
    ACTION_EXECUTE,
    SIDE_BID,
    SIDE_ASK,
)
from lob_triad.splitter import TemporalClockContentSplitter
from lob_triad.gate import DiscreteMorseImpulseGate, MorseClassification
from lob_triad.triad import SkewSymmetricTriadTieBreaker

__all__ = [
    "__version__",
    "RustLOBEngine",
    "PurePythonLOBEngine",
    "TemporalClockContentSplitter",
    "DiscreteMorseImpulseGate",
    "MorseClassification",
    "SkewSymmetricTriadTieBreaker",
    "is_rust_available",
    "ACTION_ADD",
    "ACTION_CANCEL",
    "ACTION_REPLACE",
    "ACTION_EXECUTE",
    "SIDE_BID",
    "SIDE_ASK",
]
