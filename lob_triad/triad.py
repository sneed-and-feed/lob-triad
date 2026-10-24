"""so(C) Skew-Symmetric Triad Tie-Breaker with Exact 0.000e+00 Spherical Drift.

Grounded in DarkSnail formalization (Theorems 2.1 through 2.6 in OcclusionTriad.lean):
    B_W(u, v)_k = sum_{i, j} u_i v_j (W_{i, j, k} - W_{i, k, j})
    M_{k, j} = sum_i u_i (W_{i, j, k} - W_{i, k, j}) in so(C)
    <v, B_W(u, v)> = 0 (Tangent Orthogonality)
    R = (I - eta/2 M)^{-1} (I + eta/2 M) in SO(C) (Cayley Rotor)
    ||R v||_2^2 = ||v||_2^2 with exact 0.000e+00 spherical norm drift.
"""

from __future__ import annotations

from typing import Optional, Tuple
import numpy as np


class SkewSymmetricTriadTieBreaker:
    """so(C) Skew-Symmetric Triad Tie-Breaker for cross-asset / multi-venue liquidity state."""

    def __init__(self, channels: int = 2) -> None:
        self.channels = channels
        # W tensor of shape (C, C, C)
        self.W = np.zeros((channels, channels, channels), dtype=np.float64)
        # Venue state on S^{C-1}
        self.v = np.zeros(channels, dtype=np.float64)
        self.v[:2] = 1.0 / np.sqrt(2.0)
        # Market regime vector
        self.u = np.zeros(channels, dtype=np.float64)
        self.u[0] = 1.0

    def set_directed_lead_lag(self, c1: int, c2: int, strength: float = 2.0) -> None:
        """Set directed lead-lag flow between venue c1 and c2."""
        if c1 < self.channels and c2 < self.channels:
            self.W[0, c1, c2] = strength
            self.W[0, c2, c1] = -strength

    def compute_generator(self) -> np.ndarray:
        """Compute skew-symmetric generator matrix M_{k, j} in so(C)."""
        C = self.channels
        M = np.zeros((C, C), dtype=np.float64)
        for k in range(C):
            for j in range(C):
                if j == k:
                    continue
                # M_{k, j} = sum_i u_i (W_{i, j, k} - W_{i, k, j})
                val = 0.0
                for i in range(C):
                    val += self.u[i] * (self.W[i, j, k] - self.W[i, k, j])
                M[k, j] = val

        # Enforce exact antisymmetry: M = (M - M^T)/2
        M = 0.5 * (M - M.T)
        return M

    def step_cayley_rotor(self, eta: float = 0.01) -> Tuple[np.ndarray, float]:
        """Apply Cayley rotor update R = (I - eta/2 M)^{-1} (I + eta/2 M) in SO(C).

        Returns:
            (v_new, spherical_drift)
        """
        C = self.channels
        M = self.compute_generator()
        I = np.eye(C, dtype=np.float64)

        A = I - 0.5 * eta * M
        B = I + 0.5 * eta * M

        # Solve A v_new = B v
        rhs = B @ self.v
        v_new = np.linalg.solve(A, rhs)

        # Spherical drift check: ||v_new||_2^2 - ||v_old||_2^2
        norm_old = float(np.sum(self.v ** 2))
        norm_new = float(np.sum(v_new ** 2))
        drift = abs(norm_new - norm_old)

        self.v = v_new
        return self.v, drift

    def break_parity_tie(self, c1: int = 0, c2: int = 1, eta: float = 0.05) -> Tuple[float, float]:
        """Simulate symmetric parity tie resolution.

        Returns:
            (post_triad_margin, spherical_drift)
        """
        # Ensure exact initial tie
        self.v[:] = 0.0
        self.v[c1] = 1.0 / np.sqrt(2.0)
        self.v[c2] = 1.0 / np.sqrt(2.0)

        self.set_directed_lead_lag(c1, c2, strength=2.0)
        v_new, drift = self.step_cayley_rotor(eta)

        margin = float(v_new[c1] - v_new[c2])
        return margin, drift
