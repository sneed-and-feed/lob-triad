"""C-ABI ctypes bridge to liblob_triad_rs (#![no_std] Rust SIMD kernel)."""

from __future__ import annotations

import ctypes
import os
import platform
from pathlib import Path
from typing import Optional, Tuple


def _find_rust_library() -> Optional[str]:
    """Find compiled lob_triad_rs shared library."""
    system = platform.system()
    if system == "Windows":
        lib_name = "lob_triad_rs.dll"
    elif system == "Darwin":
        lib_name = "liblob_triad_rs.dylib"
    else:
        lib_name = "liblob_triad_rs.so"

    current_dir = Path(__file__).resolve().parent
    repo_root = current_dir.parent

    candidate_paths = [
        repo_root / "target" / "release" / lib_name,
        repo_root / "target" / "debug" / lib_name,
        repo_root / "rust" / "lob_triad_rs" / "target" / "release" / lib_name,
        repo_root / "rust" / "lob_triad_rs" / "target" / "debug" / lib_name,
        current_dir / lib_name,
    ]

    for p in candidate_paths:
        if p.exists():
            return str(p)

    return None


_LIB_PATH = _find_rust_library()
_LIB: Optional[ctypes.CDLL] = None

if _LIB_PATH:
    try:
        _LIB = ctypes.CDLL(_LIB_PATH)
        _LIB.lob_arena_size_bytes.restype = ctypes.c_size_t
        _LIB.lob_arena_init.argtypes = [ctypes.c_void_p]
        _LIB.lob_arena_init.restype = ctypes.c_int32
        _LIB.lob_arena_reset.argtypes = [ctypes.c_void_p]
        _LIB.lob_arena_reset.restype = ctypes.c_int32
        _LIB.lob_arena_process_tick.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint8,
            ctypes.c_uint64,
            ctypes.c_uint8,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint64,
        ]
        _LIB.lob_arena_process_tick.restype = ctypes.c_int32
        _LIB.lob_arena_get_top_of_book.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
        ]
        _LIB.lob_arena_get_top_of_book.restype = ctypes.c_int32
        _LIB.lob_arena_get_micro_price.argtypes = [ctypes.c_void_p]
        _LIB.lob_arena_get_micro_price.restype = ctypes.c_float
        _LIB.lob_arena_get_mid_price.argtypes = [ctypes.c_void_p]
        _LIB.lob_arena_get_mid_price.restype = ctypes.c_float
        _LIB.lob_arena_get_ofi.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
        ]
        _LIB.lob_arena_get_ofi.restype = ctypes.c_int32
        _LIB.lob_arena_step_morse_gate.argtypes = [
            ctypes.c_void_p,
            ctypes.c_float,
            ctypes.c_uint64,
        ]
        _LIB.lob_arena_step_morse_gate.restype = ctypes.c_int32
        _LIB.lob_arena_evaluate_triad.argtypes = [
            ctypes.c_void_p,
            ctypes.c_float,
            ctypes.POINTER(ctypes.c_float),
        ]
        _LIB.lob_arena_evaluate_triad.restype = ctypes.c_int32
    except Exception:
        _LIB = None


def is_rust_available() -> bool:
    """Return whether the compiled Rust library is loaded."""
    return _LIB is not None


class RustLOBEngine:
    """Python ctypes interface to LOBStateArena in liblob_triad_rs."""

    def __init__(self) -> None:
        if _LIB is None:
            raise RuntimeError(
                "Rust shared library (lob_triad_rs) not found or failed to load. "
                "Run `cargo build --release` in lob-triad."
            )
        self.size_bytes = _LIB.lob_arena_size_bytes()
        # Allocate ctypes char buffer with extra 64 bytes for alignment
        self._raw_buffer = (ctypes.c_char * (self.size_bytes + 64))()
        buf_addr = ctypes.addressof(self._raw_buffer)
        aligned_addr = (buf_addr + 63) & ~63
        self._arena_ptr = ctypes.c_void_p(aligned_addr)

        res = _LIB.lob_arena_init(self._arena_ptr)
        if res != 0:
            raise RuntimeError(f"lob_arena_init failed with code {res}")

    def reset(self) -> None:
        """Reset arena state."""
        _LIB.lob_arena_reset(self._arena_ptr)

    def process_tick(
        self,
        action: int,
        order_id: int,
        side: int,
        price: int,
        volume: int,
        timestamp_ns: int = 0,
    ) -> int:
        """Process an L3 tick event (Add, Cancel, Replace, Execute)."""
        return _LIB.lob_arena_process_tick(
            self._arena_ptr,
            ctypes.c_uint8(action),
            ctypes.c_uint64(order_id),
            ctypes.c_uint8(side),
            ctypes.c_uint32(price),
            ctypes.c_uint32(volume),
            ctypes.c_uint64(timestamp_ns),
        )

    def get_top_of_book(self) -> Tuple[int, int, int, int]:
        """Return (best_bid_price, best_bid_volume, best_ask_price, best_ask_volume)."""
        bb_p = ctypes.c_uint32(0)
        bb_v = ctypes.c_uint32(0)
        ba_p = ctypes.c_uint32(0)
        ba_v = ctypes.c_uint32(0)

        _LIB.lob_arena_get_top_of_book(
            self._arena_ptr,
            ctypes.byref(bb_p),
            ctypes.byref(bb_v),
            ctypes.byref(ba_p),
            ctypes.byref(ba_v),
        )
        return bb_p.value, bb_v.value, ba_p.value, ba_v.value

    def get_mid_price(self) -> float:
        """Return mid price."""
        return float(_LIB.lob_arena_get_mid_price(self._arena_ptr))

    def get_micro_price(self) -> float:
        """Return micro price (Cont & Stoikov)."""
        return float(_LIB.lob_arena_get_micro_price(self._arena_ptr))

    def get_ofi(self) -> Tuple[float, float]:
        """Return cumulative (raw_ofi, purified_ofi)."""
        raw = ctypes.c_double(0.0)
        purified = ctypes.c_double(0.0)
        _LIB.lob_arena_get_ofi(self._arena_ptr, ctypes.byref(raw), ctypes.byref(purified))
        return raw.value, purified.value

    def step_morse_gate(self, mid_price: float, delta_t_ns: int) -> int:
        """Evaluate 3-point discrete Morse impulse gate."""
        return int(
            _LIB.lob_arena_step_morse_gate(
                self._arena_ptr,
                ctypes.c_float(mid_price),
                ctypes.c_uint64(delta_t_ns),
            )
        )

    def evaluate_triad(self, eta: float = 0.01) -> float:
        """Evaluate so(C) skew-symmetric triad tie-breaker and return spherical drift."""
        drift = ctypes.c_float(0.0)
        _LIB.lob_arena_evaluate_triad(
            self._arena_ptr,
            ctypes.c_float(eta),
            ctypes.byref(drift),
        )
        return float(drift.value)
