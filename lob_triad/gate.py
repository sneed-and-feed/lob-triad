"""3-Point Discrete Morse Impulse Gate with 1-Sample Causal Deferral and Quantile Pullback.

Grounded in DarkSnail formalization (Theorems 7d & 7e in OcclusionTriad.lean):
    I_Morse(v, z) = Delta_- v(z) . Delta_+ v(z) = (v(z) - v(z-1)) * (v(z) - v(z+1))
    I_Morse > 0 iff z is a strict local extremum.

Differentiates 1-tick glitches (GLINT_REJECTED) from flash crashes (STEP_MANEUVER).
"""

from __future__ import annotations

import enum
import math
from typing import Optional, Tuple


class MorseClassification(enum.IntEnum):
    NOMINAL = 0
    PENDING_IMPULSE = 1
    STEP_MANEUVER = 2
    GLINT_REJECTED = 3


def inv_normal_cdf(p: float) -> float:
    """Peter Acklam's rational approximation for inverse standard normal CDF Phi^{-1}(p)."""
    p = max(0.0001, min(0.9999, float(p)))
    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]
    plow = 0.02425
    phigh = 1.0 - plow

    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        num = ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        den = (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        return num / den
    elif p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        num = ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        den = (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        return -num / den
    else:
        q = p - 0.5
        r = q * q
        num = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        den = (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
        return num / den


class DiscreteMorseImpulseGate:
    """3-point discrete Morse impulse innovation gate."""

    def __init__(
        self,
        variance: float = 1.0,
        chi2_threshold: float = 10.828,
        tau_ref_ns: int = 1_000_000_000,
    ) -> None:
        self.variance = variance
        self.chi2_threshold = chi2_threshold
        self.tau_ref_ns = tau_ref_ns

        self.v_curr: float = 0.0
        self.v_prev1: float = 0.0
        self.v_prev2: float = 0.0

        self.pending_v: float = 0.0
        self.pending_dt_ns: int = 0
        self.pending_nis: float = 0.0

        self.gate_status: MorseClassification = MorseClassification.NOMINAL
        self.total_glints: int = 0
        self.total_steps: int = 0
        self.initialized: bool = False

    def reset(self) -> None:
        self.v_curr = 0.0
        self.v_prev1 = 0.0
        self.v_prev2 = 0.0
        self.pending_v = 0.0
        self.pending_dt_ns = 0
        self.pending_nis = 0.0
        self.gate_status = MorseClassification.NOMINAL
        self.total_glints = 0
        self.total_steps = 0
        self.initialized = False

    def step(self, mid_price: float, delta_t_ns: int = 100_000_000) -> MorseClassification:
        """Step the gate with new price observation and inter-arrival time."""
        v = float(mid_price)

        if not self.initialized:
            self.v_curr = v
            self.v_prev1 = v
            self.v_prev2 = v
            self.initialized = True
            return MorseClassification.NOMINAL

        if self.gate_status == MorseClassification.PENDING_IMPULSE:
            v_tm1 = self.v_curr
            v_t = self.pending_v
            v_tp1 = v

            delta_minus = v_t - v_tm1
            delta_plus = v_t - v_tp1
            i_morse = delta_minus * delta_plus

            return_diff = abs(v_tp1 - v_tm1)
            step_diff = abs(v_tp1 - v_t)
            eps = 0.01 * self.variance

            if return_diff <= eps and i_morse > 0.0:
                # Glint rejected: 1-tick spike returned to baseline
                self.gate_status = MorseClassification.GLINT_REJECTED
                self.total_glints += 1
                self.v_curr = v_tp1
                return MorseClassification.GLINT_REJECTED
            elif step_diff <= eps or return_diff > eps:
                # Step maneuver: true liquidity vacuum / structural flash crash
                self.gate_status = MorseClassification.STEP_MANEUVER
                self.total_steps += 1
                self.v_prev2 = v_tm1
                self.v_prev1 = v_t
                self.v_curr = v_tp1
                return MorseClassification.STEP_MANEUVER
            else:
                self.gate_status = MorseClassification.NOMINAL
                self.v_prev2 = self.v_prev1
                self.v_prev1 = self.pending_v
                self.v_curr = v
                return MorseClassification.NOMINAL

        diff = abs(v - self.v_curr)
        nis = (diff * diff) / max(1e-6, self.variance)

        # Dynamic pullback threshold: Phi^{-1}(1 - delta_t / tau_ref)
        dt_ratio = max(0.001, min(0.999, delta_t_ns / self.tau_ref_ns))
        phi_inv = inv_normal_cdf(1.0 - 0.5 * dt_ratio)
        dynamic_threshold = self.chi2_threshold * max(0.5, phi_inv)

        if nis > dynamic_threshold:
            # Innovation spike: enter 1-sample causal deferral
            self.gate_status = MorseClassification.PENDING_IMPULSE
            self.pending_v = v
            self.pending_dt_ns = delta_t_ns
            self.pending_nis = nis
            return MorseClassification.PENDING_IMPULSE
        else:
            self.gate_status = MorseClassification.NOMINAL
            self.v_prev2 = self.v_prev1
            self.v_prev1 = self.v_curr
            self.v_curr = v
            self.variance = 0.95 * self.variance + 0.05 * max(1e-4, diff * diff)
            return MorseClassification.NOMINAL
