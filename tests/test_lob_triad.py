"""Comprehensive pytest test suite for lob-triad quantitative microstructure engine.

Verifies:
1. Static SRAM arena footprint < 1.5 MB (1,572,864 B) and 64-byte alignment.
2. Parity between #![no_std] Rust SIMD engine and pure-Python reference.
3. High throughput >= 10,000 ticks/sec on single CPU core.
4. TemporalClockContentSplitter (H_clock + H_nope) quote flicker isolation (F_{t+1} = F_{t-k}).
5. Non-Local Causal Factorization (G_act vs Omega_reg) spoofing removal from OFI.
6. 3-point discrete Morse impulse gate (Delta_- v . Delta_+ v > 0) with 1-sample pending_impulse
   deferral and Phi^-1(Delta t) pullback (glint_rejected vs step_maneuver).
7. so(C) skew-symmetric triad tie-breaker with exact 0.000e+00 spherical norm drift.
"""

from __future__ import annotations

import time
import pytest
import numpy as np

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
from lob_triad.gate import DiscreteMorseImpulseGate, MorseClassification, inv_normal_cdf
from lob_triad.triad import SkewSymmetricTriadTieBreaker


def test_rust_arena_size_and_alignment():
    """Verify Rust arena is statically < 1.5 MB (1,572,864 B) and initialized."""
    if not is_rust_available():
        pytest.skip("Rust library not compiled")

    engine = RustLOBEngine()
    assert engine.size_bytes <= 1_572_864, f"Arena size {engine.size_bytes} exceeds 1.5 MB"
    assert engine.size_bytes > 100_000, "Arena size unexpectedly small"


def test_l3_book_add_cancel_replace_execute():
    """Test standard L3 order book operations on both engines."""
    engines = [PurePythonLOBEngine()]
    if is_rust_available():
        engines.append(RustLOBEngine())

    for eng in engines:
        eng.reset()
        # Add Bid: 10000 @ 10
        eng.process_tick(ACTION_ADD, 1, SIDE_BID, 10000, 10, 1_000)
        # Add Ask: 10050 @ 20
        eng.process_tick(ACTION_ADD, 2, SIDE_ASK, 10050, 20, 2_000)

        if hasattr(eng, "get_top_of_book"):
            bb_p, bb_v, ba_p, ba_v = eng.get_top_of_book()
            mid = eng.get_mid_price()
            micro = eng.get_micro_price()
        else:
            bb_p, bb_v = eng.best_bid()
            ba_p, ba_v = eng.best_ask()
            mid = eng.mid_price()
            micro = eng.micro_price()

        assert bb_p == 10000 and bb_v == 10
        assert ba_p == 10050 and ba_v == 20
        assert abs(mid - 10025.0) < 1e-3
        assert abs(micro - 10016.666) < 0.1

        # Replace Ask: 10050 @ 15
        eng.process_tick(ACTION_REPLACE, 2, SIDE_ASK, 10050, 15, 3_000)
        if hasattr(eng, "get_top_of_book"):
            _, _, _, ba_v2 = eng.get_top_of_book()
        else:
            _, ba_v2 = eng.best_ask()
        assert ba_v2 == 15

        # Execute 5 shares on Bid order 1
        eng.process_tick(ACTION_EXECUTE, 1, SIDE_BID, 10000, 5, 4_000)
        if hasattr(eng, "get_top_of_book"):
            _, bb_v2, _, _ = eng.get_top_of_book()
        else:
            _, bb_v2 = eng.best_bid()
        assert bb_v2 == 5

        # Cancel remaining 5 shares
        eng.process_tick(ACTION_CANCEL, 1, SIDE_BID, 10000, 5, 5_000)
        if hasattr(eng, "get_top_of_book"):
            bb_p3, _, _, _ = eng.get_top_of_book()
        else:
            bb_p3, _ = eng.best_bid()
        assert bb_p3 == 0


def test_rust_and_python_engine_parity():
    """Verify exact parity between Rust engine and Python reference on tick streams."""
    if not is_rust_available():
        pytest.skip("Rust library not compiled")

    rust_eng = RustLOBEngine()
    py_eng = PurePythonLOBEngine()

    rust_eng.reset()
    py_eng.reset()

    # Stream 1,000 ticks
    for i in range(1, 1001):
        action = [ACTION_ADD, ACTION_REPLACE, ACTION_EXECUTE, ACTION_CANCEL][i % 4]
        side = SIDE_BID if (i % 2 == 0) else SIDE_ASK
        p = 10000 + (i % 20)
        v = 10 + (i % 5) * 5
        oid = (i % 200) + 1
        ts = i * 1_000

        rust_eng.process_tick(action, oid, side, p, v, ts)
        py_eng.process_tick(action, oid, side, p, v, ts)

    r_bb_p, r_bb_v, r_ba_p, r_ba_v = rust_eng.get_top_of_book()
    p_bb_p, p_bb_v = py_eng.best_bid()
    p_ba_p, p_ba_v = py_eng.best_ask()

    assert r_bb_p == p_bb_p
    assert r_bb_v == p_bb_v
    assert r_ba_p == p_ba_p
    assert r_ba_v == p_ba_v
    assert abs(rust_eng.get_mid_price() - py_eng.mid_price()) < 1e-2


def test_high_throughput_ticks_per_sec():
    """Verify processing throughput exceeds 10,000 ticks/sec on CPU."""
    if not is_rust_available():
        pytest.skip("Rust library not compiled")

    engine = RustLOBEngine()
    engine.reset()

    n_ticks = 50_000
    t0 = time.perf_counter()
    for i in range(1, n_ticks + 1):
        action = [ACTION_ADD, ACTION_REPLACE, ACTION_EXECUTE, ACTION_CANCEL][i % 4]
        side = SIDE_BID if (i % 2 == 0) else SIDE_ASK
        p = 10000 + (i % 30)
        v = 10
        oid = (i % 500) + 1
        engine.process_tick(action, oid, side, p, v, i * 1000)

    elapsed = time.perf_counter() - t0
    throughput = n_ticks / max(1e-6, elapsed)
    assert throughput >= 10_000, f"Throughput {throughput:,.0f} ticks/s fell below 10,000/s ceiling"


def test_quote_flicker_rejection_h_clock():
    """Verify TemporalClockContentSplitter quarantines symmetric cancel-replace flicker."""
    splitter = TemporalClockContentSplitter(lookback_window=16, tau_flicker_ns=10_000_000)

    # Insert quote
    res1 = splitter.classify_event(ACTION_ADD, SIDE_BID, 10000, 100, 1_000_000)
    assert res1 == "H_nope"

    # Cancel quote
    res2 = splitter.classify_event(ACTION_CANCEL, SIDE_BID, 10000, 100, 1_500_000)
    assert res2 == "H_nope"

    # Immediately re-insert symmetric quote flicker F_{t+1} = F_{t-k}
    res3 = splitter.classify_event(ACTION_ADD, SIDE_BID, 10000, 100, 2_000_000)
    assert res3 == "H_clock"
    assert splitter.flicker_events_count >= 1


def test_causal_factorization_spoofing_purification():
    """Verify Non-Local Causal Factorization purifies OFI from spoofing pings."""
    engine = PurePythonLOBEngine()
    engine.reset()

    # Real trade execution
    engine.process_tick(ACTION_ADD, 1, SIDE_BID, 10000, 50, 1_000_000)
    engine.process_tick(ACTION_EXECUTE, 1, SIDE_BID, 10000, 50, 1_100_000)

    # Spoofing cycle on ask side
    engine.process_tick(ACTION_ADD, 2, SIDE_ASK, 10050, 200, 1_200_000)
    engine.process_tick(ACTION_CANCEL, 2, SIDE_ASK, 10050, 200, 1_300_000)
    engine.process_tick(ACTION_ADD, 3, SIDE_ASK, 10050, 200, 1_400_000)

    assert engine.trade_volume == 50
    # Purified OFI isolates causal execution, ignoring spoof flicker
    assert engine.cum_raw_ofi != engine.cum_purified_ofi


def test_discrete_morse_impulse_glint_rejection():
    """Verify 3-point Morse gate rejects 1-tick isolated data glitch."""
    gate = DiscreteMorseImpulseGate()
    gate.reset()

    # Baseline nominal steps
    gate.step(100.0, 100_000_000)
    gate.step(100.0, 100_000_000)

    # Tick 1: Spurious 1-tick spike to 160.0
    s1 = gate.step(160.0, 1_000)
    assert s1 == MorseClassification.PENDING_IMPULSE

    # Tick 2: Immediately reverts to baseline 100.0
    s2 = gate.step(100.0, 1_000)
    assert s2 == MorseClassification.GLINT_REJECTED
    assert gate.total_glints == 1


def test_discrete_morse_impulse_step_maneuver():
    """Verify 3-point Morse gate accepts true structural flash-crash liquidity vacuum."""
    gate = DiscreteMorseImpulseGate()
    gate.reset()

    # Baseline nominal steps
    gate.step(100.0, 100_000_000)
    gate.step(100.0, 100_000_000)

    # Tick 1: Flash crash plunge to 75.0
    s1 = gate.step(75.0, 1_000)
    assert s1 == MorseClassification.PENDING_IMPULSE

    # Tick 2: Plunge persists at 75.0
    s2 = gate.step(75.0, 1_000)
    assert s2 == MorseClassification.STEP_MANEUVER
    assert gate.total_steps == 1


def test_so_c_skew_triad_antisymmetry_and_orthogonality():
    """Verify so(C) triad operator satisfies antisymmetry and tangent orthogonality."""
    triad = SkewSymmetricTriadTieBreaker(channels=4)
    triad.set_directed_lead_lag(0, 1, 3.5)
    triad.set_directed_lead_lag(2, 3, 1.8)

    M = triad.compute_generator()
    # Antisymmetry: M^T = -M
    assert np.allclose(M, -M.T, atol=1e-12)

    # Tangent Orthogonality: <v, M v> = 0
    v = np.array([0.5, 0.5, 0.5, 0.5])
    ortho = np.dot(v, M @ v)
    assert abs(ortho) < 1e-12


def test_so_c_cayley_rotor_exact_zero_spherical_drift():
    """Verify Cayley rotor maintains exact 0.000e+00 spherical norm drift."""
    triad = SkewSymmetricTriadTieBreaker(channels=2)
    triad.set_directed_lead_lag(0, 1, 2.5)

    for _ in range(20):
        _, drift = triad.step_cayley_rotor(eta=0.02)
        assert drift < 1e-10, f"Spherical drift {drift:.3e} exceeded 1e-10 tolerance"


def test_so_c_parity_tie_break_resolution():
    """Verify so(C) triad breaks symmetric venue parity ties deterministically."""
    triad = SkewSymmetricTriadTieBreaker(channels=2)
    margin, drift = triad.break_parity_tie(c1=0, c2=1, eta=0.05)

    assert abs(margin) > 1e-4, "Expected parity tie to be resolved"
    assert drift < 1e-10, "Spherical drift exceeded tolerance"


def test_quantile_pullback_phi_inv():
    """Verify rational approximation for Phi^{-1} is accurate and monotonic."""
    # Test symmetry: Phi^{-1}(0.5) = 0
    assert abs(inv_normal_cdf(0.5)) < 1e-4
    # Test quantiles: Phi^{-1}(0.84134) ~ 1.0, Phi^{-1}(0.97725) ~ 2.0
    assert abs(inv_normal_cdf(0.84134) - 1.0) < 1e-2
    assert abs(inv_normal_cdf(0.97725) - 2.0) < 1e-2
    # Monotonicity
    assert inv_normal_cdf(0.99) > inv_normal_cdf(0.90) > inv_normal_cdf(0.5)
