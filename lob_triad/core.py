"""Pure-Python reference implementation of Level-3 Limit Order Book matching engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

ACTION_ADD: int = 1
ACTION_CANCEL: int = 2
ACTION_REPLACE: int = 3
ACTION_EXECUTE: int = 4

SIDE_BID: int = 0
SIDE_ASK: int = 1


@dataclass
class Order:
    order_id: int
    side: int
    price: int
    volume: int
    timestamp_ns: int
    is_flicker: bool = False
    is_causal: bool = True


@dataclass
class PriceLevel:
    price: int
    volume: int
    orders: List[Order] = field(default_factory=list)


class PurePythonLOBEngine:
    """Pure-Python reference implementation of Level-3 Limit Order Book."""

    def __init__(self) -> None:
        self.bids: Dict[int, PriceLevel] = {}  # price -> PriceLevel
        self.asks: Dict[int, PriceLevel] = {}  # price -> PriceLevel
        self.orders: Dict[int, Order] = {}     # order_id -> Order

        self.cum_raw_ofi: float = 0.0
        self.cum_purified_ofi: float = 0.0

        self.prev_best_bid: Tuple[int, int] = (0, 0)
        self.prev_best_ask: Tuple[int, int] = (0, 0)

        self.ticks_processed: int = 0
        self.trade_volume: int = 0
        self.spoof_volume: int = 0
        self.history: List[Tuple[int, int, int, int, int]] = []  # (action, side, price, vol, ts)

    def reset(self) -> None:
        """Reset state."""
        self.bids.clear()
        self.asks.clear()
        self.orders.clear()
        self.cum_raw_ofi = 0.0
        self.cum_purified_ofi = 0.0
        self.prev_best_bid = (0, 0)
        self.prev_best_ask = (0, 0)
        self.ticks_processed = 0
        self.trade_volume = 0
        self.spoof_volume = 0
        self.history.clear()

    def best_bid(self) -> Tuple[int, int]:
        """Return (best_bid_price, best_bid_volume). Highest price first."""
        if not self.bids:
            return (0, 0)
        max_p = max(self.bids.keys())
        return (max_p, self.bids[max_p].volume)

    def best_ask(self) -> Tuple[int, int]:
        """Return (best_ask_price, best_ask_volume). Lowest price first."""
        if not self.asks:
            return (0, 0)
        min_p = min(self.asks.keys())
        return (min_p, self.asks[min_p].volume)

    def mid_price(self) -> float:
        """Return mid price."""
        bb_p, _ = self.best_bid()
        ba_p, _ = self.best_ask()
        if bb_p > 0 and ba_p > 0:
            return (bb_p + ba_p) * 0.5
        elif bb_p > 0:
            return float(bb_p)
        else:
            return float(ba_p)

    def micro_price(self) -> float:
        """Return Cont & Stoikov micro price."""
        bb_p, bb_v = self.best_bid()
        ba_p, ba_v = self.best_ask()
        total_v = bb_v + ba_v
        if total_v > 0 and bb_p > 0 and ba_p > 0:
            return (bb_v * ba_p + ba_v * bb_p) / total_v
        return self.mid_price()

    def _check_flicker(self, action: int, side: int, price: int, volume: int) -> bool:
        """Check if incoming quote is symmetric cancel-replace quote flicker."""
        if action in (ACTION_ADD, ACTION_REPLACE):
            lookback = self.history[-16:]
            for past_action, past_side, past_p, past_v, _ in reversed(lookback):
                if past_p == price and past_side == side:
                    if past_action == ACTION_CANCEL and past_v == volume:
                        return True
        return False

    def process_tick(
        self,
        action: int,
        order_id: int,
        side: int,
        price: int,
        volume: int,
        timestamp_ns: int = 0,
    ) -> int:
        """Process an L3 order event."""
        self.ticks_processed += 1
        prev_bb_p, prev_bb_v = self.best_bid()
        prev_ba_p, prev_ba_v = self.best_ask()

        is_flicker = self._check_flicker(action, side, price, volume)

        if action == ACTION_ADD:
            order = Order(
                order_id=order_id,
                side=side,
                price=price,
                volume=volume,
                timestamp_ns=timestamp_ns,
                is_flicker=is_flicker,
                is_causal=not is_flicker,
            )
            self.orders[order_id] = order
            book = self.bids if side == SIDE_BID else self.asks
            if price not in book:
                book[price] = PriceLevel(price=price, volume=0)
            book[price].volume += volume
            book[price].orders.append(order)

        elif action == ACTION_CANCEL:
            if order_id in self.orders:
                order = self.orders.pop(order_id)
                book = self.bids if order.side == SIDE_BID else self.asks
                if order.price in book:
                    level = book[order.price]
                    level.volume = max(0, level.volume - order.volume)
                    level.orders = [o for o in level.orders if o.order_id != order_id]
                    if level.volume == 0:
                        del book[order.price]
                if not order.is_causal:
                    self.spoof_volume += order.volume

        elif action == ACTION_REPLACE:
            if order_id in self.orders:
                old_order = self.orders[order_id]
                old_book = self.bids if old_order.side == SIDE_BID else self.asks
                if old_order.price in old_book:
                    level = old_book[old_order.price]
                    level.volume = max(0, level.volume - old_order.volume)
                    level.orders = [o for o in level.orders if o.order_id != order_id]
                    if level.volume == 0:
                        del old_book[old_order.price]

                new_order = Order(
                    order_id=order_id,
                    side=side,
                    price=price,
                    volume=volume,
                    timestamp_ns=timestamp_ns,
                    is_flicker=is_flicker,
                    is_causal=not is_flicker,
                )
                self.orders[order_id] = new_order
                new_book = self.bids if side == SIDE_BID else self.asks
                if price not in new_book:
                    new_book[price] = PriceLevel(price=price, volume=0)
                new_book[price].volume += volume
                new_book[price].orders.append(new_order)

        elif action == ACTION_EXECUTE:
            if order_id in self.orders:
                order = self.orders[order_id]
                exec_vol = min(order.volume, volume)
                order.volume -= exec_vol
                book = self.bids if order.side == SIDE_BID else self.asks
                if order.price in book:
                    level = book[order.price]
                    level.volume = max(0, level.volume - exec_vol)
                    if level.volume == 0:
                        del book[order.price]
                if order.volume == 0:
                    del self.orders[order_id]
                self.trade_volume += exec_vol

        # Update OFI (Cont, Kukanov & Stoikov 2014)
        new_bb_p, new_bb_v = self.best_bid()
        new_ba_p, new_ba_v = self.best_ask()

        delta_bid_ofi = 0.0
        if prev_bb_p == 0:
            delta_bid_ofi = float(new_bb_v)
        elif new_bb_p == 0:
            delta_bid_ofi = -float(prev_bb_v)
        elif new_bb_p > prev_bb_p:
            delta_bid_ofi = float(new_bb_v)
        elif new_bb_p == prev_bb_p:
            delta_bid_ofi = float(new_bb_v - prev_bb_v)
        else:
            delta_bid_ofi = -float(prev_bb_v)

        delta_ask_ofi = 0.0
        if prev_ba_p == 0:
            delta_ask_ofi = float(new_ba_v)
        elif new_ba_p == 0:
            delta_ask_ofi = -float(prev_ba_v)
        elif new_ba_p < prev_ba_p:
            delta_ask_ofi = float(new_ba_v)
        elif new_ba_p == prev_ba_p:
            delta_ask_ofi = float(new_ba_v - prev_ba_v)
        else:
            delta_ask_ofi = -float(prev_ba_v)

        step_ofi = delta_bid_ofi - delta_ask_ofi
        self.cum_raw_ofi += step_ofi
        if not is_flicker:
            self.cum_purified_ofi += step_ofi

        self.history.append((action, side, price, volume, timestamp_ns))
        return 0
