"""CLI entrypoint for lob-triad quantitative microstructure engine."""

from __future__ import annotations

import argparse
import sys
import time
from typing import List

from lob_triad.arena import RustLOBEngine, is_rust_available
from lob_triad.core import PurePythonLOBEngine, ACTION_ADD, ACTION_CANCEL, ACTION_REPLACE, ACTION_EXECUTE, SIDE_BID, SIDE_ASK
from lob_triad.gate import DiscreteMorseImpulseGate, MorseClassification
from lob_triad.triad import SkewSymmetricTriadTieBreaker


def run_benchmark(num_ticks: int = 50_000, use_rust: bool = True) -> None:
    """Run tick throughput and microstructural telemetry benchmark."""
    print("=" * 65)
    print("  lob-triad: Level-3 Limit Order Book & Microstructure Tomography")
    print("=" * 65)

    if use_rust and is_rust_available():
        engine = RustLOBEngine()
        print(f"Engine Backend      : Rust SIMD (LOBStateArena: {engine.size_bytes:,} B < 1.5 MB)")
    else:
        engine = PurePythonLOBEngine()
        print("Engine Backend      : Pure Python Reference")

    gate = DiscreteMorseImpulseGate()
    triad = SkewSymmetricTriadTieBreaker()

    print(f"Processing Batch    : {num_ticks:,} L3 tick events...")
    t0 = time.perf_counter()

    for i in range(num_ticks):
        action = [ACTION_ADD, ACTION_REPLACE, ACTION_EXECUTE, ACTION_CANCEL][i % 4]
        side = SIDE_BID if (i % 2 == 0) else SIDE_ASK
        price = 10000 + (i % 25)
        volume = 10 + (i % 5) * 5
        order_id = (i % 1000) + 1
        ts_ns = i * 1_000

        engine.process_tick(action, order_id, side, price, volume, ts_ns)

    elapsed = time.perf_counter() - t0
    throughput = num_ticks / max(1e-6, elapsed)

    if hasattr(engine, "get_top_of_book"):
        bb_p, bb_v, ba_p, ba_v = engine.get_top_of_book()
        mid = engine.get_mid_price()
        micro = engine.get_micro_price()
        raw_ofi, pur_ofi = engine.get_ofi()
    else:
        bb_p, bb_v = engine.best_bid()
        ba_p, ba_v = engine.best_ask()
        mid = engine.mid_price()
        micro = engine.micro_price()
        raw_ofi, pur_ofi = engine.cum_raw_ofi, engine.cum_purified_ofi

    print("-" * 65)
    print(f"Elapsed Time        : {elapsed * 1000.0:.2f} ms")
    print(f"Throughput          : {throughput:,.0f} ticks/sec (Target: >= 10,000)")
    print(f"Best Bid            : ${bb_p / 100.0:.2f} (x{bb_v})")
    print(f"Best Ask            : ${ba_p / 100.0:.2f} (x{ba_v})")
    print(f"Mid Price           : ${mid / 100.0:.2f}")
    print(f"Micro Price         : ${micro / 100.0:.2f}")
    print(f"Raw OFI             : {raw_ofi:,.1f}")
    print(f"Purified OFI        : {pur_ofi:,.1f}")

    # Morse gate benchmark
    gate.step(100.0, 100_000_000)
    gate.step(100.0, 100_000_000)
    res_glint1 = gate.step(150.0, 1_000)
    res_glint2 = gate.step(100.0, 1_000)
    print(f"Morse Glint Filter  : Glint Rejected = {res_glint2 == MorseClassification.GLINT_REJECTED}")

    # Triad tie breaker
    margin, drift = triad.break_parity_tie()
    print(f"so(C) Triad TieBreak: Margin = {margin:+.4f}, Spherical Drift = {drift:.3e}")
    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(description="lob-triad L3 Microstructure Engine CLI")
    parser.add_argument("--ticks", type=int, default=50_000, help="Number of ticks to benchmark")
    parser.add_argument("--pure-python", action="store_true", help="Force pure Python engine")
    args = parser.parse_args()

    run_benchmark(num_ticks=args.ticks, use_rust=not args.pure_python)


if __name__ == "__main__":
    main()
