"""TemporalClockContentSplitter (H_clock + H_nope).

Decomposes Level-3 order book flow via discrete continuity:
    Delta_t rho_v(p, t) + nabla . J_v(p, t) = sigma(p, t)

- H_clock: Cyclic, symmetric quote flicker F_{t+1}(p) = F_{t-k}(p) with sigma = 0.
- H_nope: Irreversible causal order flow with real executions (sigma != 0) or net liquidity accumulation.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple


class TemporalClockContentSplitter:
    """Isolates high-frequency symmetric cancel-replace quote flicker from causal order flow."""

    def __init__(self, lookback_window: int = 16, tau_flicker_ns: int = 5_000_000) -> None:
        self.lookback_window = lookback_window
        self.tau_flicker_ns = tau_flicker_ns
        self.history: List[Tuple[int, int, int, int, int]] = []  # (action, side, price, volume, ts_ns)
        self.clock_levels: Set[Tuple[int, int]] = set()  # (side, price) in H_clock
        self.nope_levels: Set[Tuple[int, int]] = set()   # (side, price) in H_nope
        self.flicker_events_count: int = 0
        self.causal_events_count: int = 0

    def reset(self) -> None:
        self.history.clear()
        self.clock_levels.clear()
        self.nope_levels.clear()
        self.flicker_events_count = 0
        self.causal_events_count = 0

    def classify_event(
        self,
        action: int,
        side: int,
        price: int,
        volume: int,
        timestamp_ns: int,
    ) -> str:
        """Classify incoming event as 'H_clock' (flicker) or 'H_nope' (causal).

        Returns:
            'H_clock' if symmetric cancel-replace flicker detected.
            'H_nope' if irreversible or execution-linked.
        """
        key = (side, price)

        # Action 4 (EXECUTE) is strictly irreversible -> H_nope
        if action == 4:
            self.nope_levels.add(key)
            self.clock_levels.discard(key)
            self.causal_events_count += 1
            self.history.append((action, side, price, volume, timestamp_ns))
            return "H_nope"

        # Check for symmetric cancellation recurrence in recent history
        if action in (1, 3):  # ADD or REPLACE
            lookback = self.history[-self.lookback_window :]
            for past_action, past_side, past_price, past_volume, past_ts in reversed(lookback):
                if past_price == price and past_side == side:
                    # Symmetric cancellation match: cancelled identical volume within flicker window
                    dt = timestamp_ns - past_ts
                    if past_action == 2 and past_volume == volume and dt <= self.tau_flicker_ns:
                        self.clock_levels.add(key)
                        self.flicker_events_count += 1
                        self.history.append((action, side, price, volume, timestamp_ns))
                        return "H_clock"

        self.nope_levels.add(key)
        self.causal_events_count += 1
        self.history.append((action, side, price, volume, timestamp_ns))
        return "H_nope"
