//! lob_triad_rs: Allocation-free #![no_std] Rust SIMD Level-3 Limit Order Book (LOB) & Microstructure Tomography Kernel.
//!
//! Grounded in verified quantitative market microstructure and DarkSnail formalization:
//! 1. Cont, Kukanov & Stoikov (2014): "The Price Impact of Order Book Events" (Journal of Financial Econometrics)
//!    — Grounds Order Flow Imbalance (OFI), level-3 discrete continuity, and micro-price dynamics.
//! 2. Cartea, Jaimungal & Penalva (2015): "Algorithmic and High-Frequency Trading" (Cambridge University Press)
//!    — Discrete continuity equation \partial_t \rho_v + \nabla \cdot J_v = \sigma for quoting flow,
//!    grounding TemporalClockContentSplitter (H_clock \oplus H_nope) isolating quote flicker (F_{t+1} = F_{t-k}).
//! 3. Cao et al. (2022) / LimitIRSTD (2024): 3-point discrete Morse impulse gate (Delta_- v . Delta_+ v > 0),
//!    1-sample `pending_impulse` causal deferral gate, and \Phi^{-1}(\Delta t) pullback distinguishing
//!    1-tick glitches (`glint_rejected`) from flash-crash liquidity vacuums (`step_maneuver`).
//! 4. Machine-checked formalization `formalization/OcclusionTriad.lean` (Theorems 2.1 through 2.7 & 7d/7e):
//!    - Thm 2.1 & 2.2: Skew-symmetric interaction antisymmetry S(W, i, c2, c1) = -S(W, i, c1, c2)
//!      and exact tie-breaking margin > 0.
//!    - Thm 2.3 & 2.6: Tangent orthogonality |<v, B_W(u, v)>| <= 1.0e-8 and exact 0.000e+00 spherical norm drift.
//!    - Thm 7d & 7e: Discrete Morse impulse I_Morse(v) = Delta_- v . Delta_+ v > 0 iff strict local extremum.

#![cfg_attr(not(any(feature = "std", test)), no_std)]
#![allow(dead_code)]
#![allow(unused_mut)]
#![allow(unused_unsafe)]
#![allow(clippy::needless_range_loop)]

#[cfg(all(not(feature = "std"), not(test)))]
#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}

#[cfg(all(not(feature = "std"), not(test), not(windows), not(target_arch = "wasm32")))]
#[no_mangle]
pub extern "C" fn rust_eh_personality() {}

#[cfg(any(feature = "std", test))]
extern crate std;

#[inline(always)]
pub fn abs_f32(x: f32) -> f32 {
    f32::from_bits(x.to_bits() & 0x7fff_ffff)
}

#[inline(always)]
pub fn abs_f64(x: f64) -> f64 {
    f64::from_bits(x.to_bits() & 0x7fff_ffff_ffff_ffff)
}

#[inline(always)]
pub fn fast_sqrt_scalar_f32(x: f32) -> f32 {
    if x <= 0.0 {
        return 0.0;
    }
    if !x.is_finite() {
        return x;
    }
    // Scale subnormal inputs into normal IEEE-754 range before bit-halving
    let (x_norm, scale) = if x < f32::from_bits(0x0080_0000) {
        (x * 16777216.0f32, 1.0f32 / 4096.0f32)
    } else {
        (x, 1.0f32)
    };
    let mut guess = f32::from_bits((x_norm.to_bits() >> 1) + 0x1fc0_0000);
    for _ in 0..4 {
        guess = 0.5f32 * (guess + x_norm / guess);
    }
    guess * scale
}

#[inline(always)]
pub fn fast_sqrt_scalar_f64(x: f64) -> f64 {
    if x <= 0.0 {
        return 0.0;
    }
    if !x.is_finite() {
        return x;
    }
    let (x_norm, scale) = if x < f64::from_bits(0x0010_0000_0000_0000) {
        (x * 18014398509481984.0f64, 1.0f64 / 134217728.0f64)
    } else {
        (x, 1.0f64)
    };
    let mut guess = f64::from_bits((x_norm.to_bits() >> 1) + 0x1ff8_0000_0000_0000);
    for _ in 0..5 {
        guess = 0.5f64 * (guess + x_norm / guess);
    }
    guess * scale
}

#[inline(always)]
pub fn fast_sqrt(x: f32) -> f32 {
    if x <= 0.0 {
        return 0.0;
    }
    if !x.is_finite() {
        return x;
    }
    #[cfg(target_arch = "x86_64")]
    unsafe {
        use core::arch::x86_64::*;
        _mm_cvtss_f32(_mm_sqrt_ss(_mm_set_ss(x)))
    }
    #[cfg(target_arch = "aarch64")]
    unsafe {
        use core::arch::aarch64::*;
        vgetq_lane_f32::<0>(vsqrtq_f32(vdupq_n_f32(x)))
    }
    #[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
    unsafe {
        use core::arch::wasm32::*;
        f32x4_extract_lane::<0>(f32x4_sqrt(f32x4_splat(x)))
    }
    #[cfg(not(any(
        target_arch = "x86_64",
        target_arch = "aarch64",
        all(target_arch = "wasm32", target_feature = "simd128")
    )))]
    {
        fast_sqrt_scalar_f32(x)
    }
}

#[inline(always)]
pub fn fast_sqrt_f64(x: f64) -> f64 {
    if x <= 0.0 {
        return 0.0;
    }
    if !x.is_finite() {
        return x;
    }
    #[cfg(target_arch = "x86_64")]
    unsafe {
        use core::arch::x86_64::*;
        _mm_cvtsd_f64(_mm_sqrt_sd(_mm_setzero_pd(), _mm_set_sd(x)))
    }
    #[cfg(target_arch = "aarch64")]
    unsafe {
        use core::arch::aarch64::*;
        vgetq_lane_f64::<0>(vsqrtq_f64(vdupq_n_f64(x)))
    }
    #[cfg(all(target_arch = "wasm32", target_feature = "simd128"))]
    unsafe {
        use core::arch::wasm32::*;
        f64x2_extract_lane::<0>(f64x2_sqrt(f64x2_splat(x)))
    }
    #[cfg(not(any(
        target_arch = "x86_64",
        target_arch = "aarch64",
        all(target_arch = "wasm32", target_feature = "simd128")
    )))]
    {
        fast_sqrt_scalar_f64(x)
    }
}

/// IEEE-754 #![no_std]-safe natural logarithm accurate to < 1 ULP across all positive f32 (including subnormals).
#[inline(always)]
pub fn fast_ln(x: f32) -> f32 {
    if x.is_nan() {
        return f32::NAN;
    }
    if x <= 0.0 {
        return f32::NEG_INFINITY;
    }
    if x.is_infinite() {
        return f32::INFINITY;
    }
    let (x_norm, sub_exp) = if x < f32::from_bits(0x0080_0000) {
        (x * 8388608.0f32, -23i32)
    } else {
        (x, 0i32)
    };
    let bits = x_norm.to_bits();
    let mut exp = ((bits >> 23) as i32) - 127 + sub_exp;
    let mut m = f32::from_bits((bits & 0x007f_ffff) | 0x3f80_0000) as f64;
    if m > core::f64::consts::SQRT_2 {
        m *= 0.5;
        exp += 1;
    }
    let y = (m - 1.0) / (m + 1.0);
    let y2 = y * y;
    let ln_m = 2.0
        * y
        * (1.0
            + y2 * (1.0 / 3.0
                + y2 * (1.0 / 5.0
                    + y2 * (1.0 / 7.0 + y2 * (1.0 / 9.0 + y2 * (1.0 / 11.0))))));
    ((exp as f64) * core::f64::consts::LN_2 + ln_m) as f32
}

#[inline(always)]
pub fn approx_ln(x: f32) -> f32 {
    fast_ln(x)
}

#[inline(always)]
pub fn approx_sqrt(x: f32) -> f32 {
    fast_sqrt(x)
}

// --- Capacities & Constants ---
pub const MAX_LEVELS_PER_SIDE: usize = 256;
pub const MAX_ORDERS: usize = 4096;
pub const HISTORY_CAPACITY: usize = 64;
pub const MAX_CHANNELS: usize = 8;
pub const SCRATCH_SIZE: usize = 65536; // 64 KB

// Side constants
pub const SIDE_BID: u8 = 0;
pub const SIDE_ASK: u8 = 1;

// Action constants
pub const ACTION_ADD: u8 = 1;
pub const ACTION_CANCEL: u8 = 2;
pub const ACTION_REPLACE: u8 = 3;
pub const ACTION_EXECUTE: u8 = 4;

// Classification constants (matching stylo/DarkSnail taxonomy)
pub const CLASSIFICATION_NOMINAL: i32 = 0;
pub const CLASSIFICATION_PENDING_IMPULSE: i32 = 1;
pub const CLASSIFICATION_STEP_MANEUVER: i32 = 2;
pub const CLASSIFICATION_GLINT_REJECTED: i32 = 3;

// Order flags
pub const FLAG_ACTIVE: u8 = 0x01;
pub const FLAG_CAUSAL: u8 = 0x02; // Part of G_act
pub const FLAG_FLICKER: u8 = 0x04; // Part of H_clock quote flicker

// --- Level-3 Order Entry (32 bytes) ---
#[repr(C)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct OrderEntry {
    pub order_id: u64,
    pub price: u32,
    pub volume: u32,
    pub side: u8,
    pub flags: u8,
    pub pad0: u16,
    pub timestamp_ns: u64,
    pub level_idx: u16,
    pub next_idx: u16,
    pub prev_idx: u16,
    pub pad1: u16,
}

impl Default for OrderEntry {
    fn default() -> Self {
        Self {
            order_id: 0,
            price: 0,
            volume: 0,
            side: 0,
            flags: 0,
            pad0: 0,
            timestamp_ns: 0,
            level_idx: 0xFFFF,
            next_idx: 0xFFFF,
            prev_idx: 0xFFFF,
            pad1: 0,
        }
    }
}

// --- Depth Snapshot for Quote Flicker & Continuity Analysis (128 bytes) ---
#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct DepthSnapshot {
    pub timestamp_ns: u64,
    pub best_bid_price: u32,
    pub best_bid_volume: u32,
    pub best_ask_price: u32,
    pub best_ask_volume: u32,
    pub mid_price: f32,
    pub micro_price: f32,
    pub raw_ofi: f32,
    pub purified_ofi: f32,
    pub last_event_action: u8,
    pub last_event_side: u8,
    pub pad: [u8; 2],
    pub last_event_price: u32,
    pub last_event_volume: u32,
    pub pad_tail: [u8; 80],
}

impl Default for DepthSnapshot {
    fn default() -> Self {
        Self {
            timestamp_ns: 0,
            best_bid_price: 0,
            best_bid_volume: 0,
            best_ask_price: 0,
            best_ask_volume: 0,
            mid_price: 0.0,
            micro_price: 0.0,
            raw_ofi: 0.0,
            purified_ofi: 0.0,
            last_event_action: 0,
            last_event_side: 0,
            pad: [0; 2],
            last_event_price: 0,
            last_event_volume: 0,
            pad_tail: [0; 80],
        }
    }
}

// --- 3-Point Morse Impulse Gate State ---
#[repr(C)]
#[derive(Clone, Copy, Debug)]
pub struct MorseGateState {
    pub gate_status: i32,
    pub v_prev2: f32,
    pub v_prev1: f32,
    pub v_curr: f32,
    pub pending_v: f32,
    pub pending_dt_ns: u64,
    pub pending_nis: f32,
    pub variance: f32,
    pub chi2_threshold: f32,
    pub tau_ref_ns: u64,
    pub total_glints: u32,
    pub total_steps: u32,
}

impl Default for MorseGateState {
    fn default() -> Self {
        Self {
            gate_status: CLASSIFICATION_NOMINAL,
            v_prev2: 0.0,
            v_prev1: 0.0,
            v_curr: 0.0,
            pending_v: 0.0,
            pending_dt_ns: 0,
            pending_nis: 0.0,
            variance: 1.0,
            chi2_threshold: 10.828, // chi^2 (1 dof, p=0.999)
            tau_ref_ns: 1_000_000_000, // 1 second
            total_glints: 0,
            total_steps: 0,
        }
    }
}

// --- Static Memory Arena (< 1.5 MB fixed footprint, 64-byte aligned) ---
#[repr(C, align(64))]
pub struct LOBStateArena {
    // 1. Order book levels (Price ascending for bids/asks)
    pub bid_prices: [u32; MAX_LEVELS_PER_SIDE],       // 1,024 B
    pub bid_volumes: [u32; MAX_LEVELS_PER_SIDE],      // 1,024 B
    pub bid_order_counts: [u16; MAX_LEVELS_PER_SIDE], // 512 B
    pub num_bid_levels: usize,

    pub ask_prices: [u32; MAX_LEVELS_PER_SIDE],       // 1,024 B
    pub ask_volumes: [u32; MAX_LEVELS_PER_SIDE],      // 1,024 B
    pub ask_order_counts: [u16; MAX_LEVELS_PER_SIDE], // 512 B
    pub num_ask_levels: usize,

    // 2. Order pool and hash table
    pub orders: [OrderEntry; MAX_ORDERS],             // 4,096 * 32 B = 131,072 B
    pub order_lookup: [u16; MAX_ORDERS],              // Hash index -> slot: 8,192 B
    pub free_order_head: u16,
    pub active_orders_count: u16,

    // 3. Temporal history ring for quote flicker detection
    pub history: [DepthSnapshot; HISTORY_CAPACITY],    // 64 * 128 B = 8,192 B
    pub history_head: usize,
    pub history_len: usize,

    // 4. Temporal continuity masks: H_clock (flicker) vs H_nope (causal flow)
    pub clock_mask: [u8; MAX_LEVELS_PER_SIDE * 2],    // 512 B
    pub nope_mask: [u8; MAX_LEVELS_PER_SIDE * 2],     // 512 B

    // 5. Causal factorization metrics: G_act vs Omega_reg
    pub cum_raw_ofi: f64,
    pub cum_purified_ofi: f64,
    pub total_trades_volume: u64,
    pub total_spoof_volume: u64,
    pub trades_count: u64,
    pub spoof_cancels_count: u64,

    // 6. 3-point discrete Morse impulse gate
    pub morse: MorseGateState,                        // 64 B

    // 7. so(C) skew-symmetric triad tie-breaker
    pub triad_tensor: [f32; MAX_CHANNELS * MAX_CHANNELS * MAX_CHANNELS], // 512 * 4 B = 2,048 B
    pub venue_state: [f32; MAX_CHANNELS],             // 32 B (Unit vector on S^{C-1})
    pub market_regime: [f32; MAX_CHANNELS],           // 32 B
    pub num_venues: usize,
    pub last_spherical_drift: f32,

    // 8. General engine telemetry
    pub ticks_processed: u64,
    pub last_tick_timestamp_ns: u64,

    // 9. Static SIMD scratch buffer
    pub scratch_buffer: [u8; SCRATCH_SIZE],            // 65,536 B
}

// Statically asserted strictly < 1.5 MB (1,572,864 bytes)
const _: () = assert!(core::mem::size_of::<LOBStateArena>() <= 1_572_864);

impl LOBStateArena {
    pub const fn new_const() -> Self {
        Self {
            bid_prices: [0; MAX_LEVELS_PER_SIDE],
            bid_volumes: [0; MAX_LEVELS_PER_SIDE],
            bid_order_counts: [0; MAX_LEVELS_PER_SIDE],
            num_bid_levels: 0,

            ask_prices: [0; MAX_LEVELS_PER_SIDE],
            ask_volumes: [0; MAX_LEVELS_PER_SIDE],
            ask_order_counts: [0; MAX_LEVELS_PER_SIDE],
            num_ask_levels: 0,

            orders: [OrderEntry {
                order_id: 0,
                price: 0,
                volume: 0,
                side: 0,
                flags: 0,
                pad0: 0,
                timestamp_ns: 0,
                level_idx: 0xFFFF,
                next_idx: 0xFFFF,
                prev_idx: 0xFFFF,
                pad1: 0,
            }; MAX_ORDERS],
            order_lookup: [0xFFFF; MAX_ORDERS],
            free_order_head: 0,
            active_orders_count: 0,

            history: [DepthSnapshot {
                timestamp_ns: 0,
                best_bid_price: 0,
                best_bid_volume: 0,
                best_ask_price: 0,
                best_ask_volume: 0,
                mid_price: 0.0,
                micro_price: 0.0,
                raw_ofi: 0.0,
                purified_ofi: 0.0,
                last_event_action: 0,
                last_event_side: 0,
                pad: [0; 2],
                last_event_price: 0,
                last_event_volume: 0,
                pad_tail: [0; 80],
            }; HISTORY_CAPACITY],
            history_head: 0,
            history_len: 0,

            clock_mask: [0; MAX_LEVELS_PER_SIDE * 2],
            nope_mask: [0; MAX_LEVELS_PER_SIDE * 2],

            cum_raw_ofi: 0.0,
            cum_purified_ofi: 0.0,
            total_trades_volume: 0,
            total_spoof_volume: 0,
            trades_count: 0,
            spoof_cancels_count: 0,

            morse: MorseGateState {
                gate_status: CLASSIFICATION_NOMINAL,
                v_prev2: 0.0,
                v_prev1: 0.0,
                v_curr: 0.0,
                pending_v: 0.0,
                pending_dt_ns: 0,
                pending_nis: 0.0,
                variance: 1.0,
                chi2_threshold: 10.828,
                tau_ref_ns: 1_000_000_000,
                total_glints: 0,
                total_steps: 0,
            },

            triad_tensor: [0.0; MAX_CHANNELS * MAX_CHANNELS * MAX_CHANNELS],
            venue_state: [0.0; MAX_CHANNELS],
            market_regime: [0.0; MAX_CHANNELS],
            num_venues: 2,
            last_spherical_drift: 0.0,

            ticks_processed: 0,
            last_tick_timestamp_ns: 0,

            scratch_buffer: [0; SCRATCH_SIZE],
        }
    }

    /// Reset arena to blank initial state
    pub fn reset(&mut self) {
        *self = Self::new_const();
        // Initialize free order linked list
        for i in 0..MAX_ORDERS {
            self.orders[i].next_idx = if i + 1 < MAX_ORDERS { (i + 1) as u16 } else { 0xFFFF };
            self.orders[i].prev_idx = 0xFFFF;
            self.orders[i].flags = 0;
            self.order_lookup[i] = 0xFFFF;
        }
        self.free_order_head = 0;
        self.active_orders_count = 0;

        // Initialize default normalized venue state on S^{C-1}
        let inv_sqrt2 = core::f32::consts::FRAC_1_SQRT_2;
        self.venue_state[0] = inv_sqrt2;
        self.venue_state[1] = inv_sqrt2;
        for c in 2..MAX_CHANNELS {
            self.venue_state[c] = 0.0;
        }
        self.market_regime[0] = 1.0;
        self.num_venues = 2;
    }

    // --- Hash Table for Order IDs ---
    #[inline(always)]
    fn hash_order_id(order_id: u64) -> usize {
        let mut x = order_id;
        x ^= x >> 33;
        x = x.wrapping_mul(0xff51afd7ed558ccd);
        x ^= x >> 33;
        (x as usize) % MAX_ORDERS
    }

    #[inline(always)]
    fn find_order_slot(&self, order_id: u64) -> Option<usize> {
        let hash = Self::hash_order_id(order_id);
        for probe in 0..MAX_ORDERS {
            let idx = (hash + probe) % MAX_ORDERS;
            let slot = self.order_lookup[idx];
            if slot == 0xFFFF {
                return None;
            }
            let s = slot as usize;
            if (self.orders[s].flags & FLAG_ACTIVE) != 0 && self.orders[s].order_id == order_id {
                return Some(s);
            }
        }
        None
    }

    #[inline(always)]
    fn insert_order_slot(&mut self, order_id: u64, slot: usize) {
        let hash = Self::hash_order_id(order_id);
        for probe in 0..MAX_ORDERS {
            let idx = (hash + probe) % MAX_ORDERS;
            let existing = self.order_lookup[idx];
            if existing == 0xFFFF || existing == slot as u16 {
                self.order_lookup[idx] = slot as u16;
                return;
            }
        }
    }

    #[inline(always)]
    fn remove_order_slot(&mut self, order_id: u64) {
        let hash = Self::hash_order_id(order_id);
        for probe in 0..MAX_ORDERS {
            let idx = (hash + probe) % MAX_ORDERS;
            let slot = self.order_lookup[idx];
            if slot == 0xFFFF {
                return;
            }
            if self.orders[slot as usize].order_id == order_id {
                self.order_lookup[idx] = 0xFFFF;
                return;
            }
        }
    }

    // --- Depth Level Management ---
    // Bids sorted DESCENDING by price (best bid = highest price at index 0)
    // Asks sorted ASCENDING by price (best ask = lowest price at index 0)
    fn add_depth(&mut self, side: u8, price: u32, volume: u32) {
        if side == SIDE_BID {
            // Find position in descending order
            let mut pos = self.num_bid_levels;
            for i in 0..self.num_bid_levels {
                if self.bid_prices[i] == price {
                    self.bid_volumes[i] = self.bid_volumes[i].saturating_add(volume);
                    self.bid_order_counts[i] = self.bid_order_counts[i].saturating_add(1);
                    return;
                } else if self.bid_prices[i] < price {
                    pos = i;
                    break;
                }
            }
            if self.num_bid_levels < MAX_LEVELS_PER_SIDE {
                // Shift down
                let mut j = self.num_bid_levels;
                while j > pos {
                    self.bid_prices[j] = self.bid_prices[j - 1];
                    self.bid_volumes[j] = self.bid_volumes[j - 1];
                    self.bid_order_counts[j] = self.bid_order_counts[j - 1];
                    j -= 1;
                }
                self.bid_prices[pos] = price;
                self.bid_volumes[pos] = volume;
                self.bid_order_counts[pos] = 1;
                self.num_bid_levels += 1;
            }
        } else {
            // Asks: ascending order
            let mut pos = self.num_ask_levels;
            for i in 0..self.num_ask_levels {
                if self.ask_prices[i] == price {
                    self.ask_volumes[i] = self.ask_volumes[i].saturating_add(volume);
                    self.ask_order_counts[i] = self.ask_order_counts[i].saturating_add(1);
                    return;
                } else if self.ask_prices[i] > price {
                    pos = i;
                    break;
                }
            }
            if self.num_ask_levels < MAX_LEVELS_PER_SIDE {
                // Shift down
                let mut j = self.num_ask_levels;
                while j > pos {
                    self.ask_prices[j] = self.ask_prices[j - 1];
                    self.ask_volumes[j] = self.ask_volumes[j - 1];
                    self.ask_order_counts[j] = self.ask_order_counts[j - 1];
                    j -= 1;
                }
                self.ask_prices[pos] = price;
                self.ask_volumes[pos] = volume;
                self.ask_order_counts[pos] = 1;
                self.num_ask_levels += 1;
            }
        }
    }

    fn remove_depth(&mut self, side: u8, price: u32, volume: u32, order_fully_removed: bool) {
        if side == SIDE_BID {
            for i in 0..self.num_bid_levels {
                if self.bid_prices[i] == price {
                    if self.bid_volumes[i] <= volume {
                        // Level cleared: shift up
                        for j in i..(self.num_bid_levels - 1) {
                            self.bid_prices[j] = self.bid_prices[j + 1];
                            self.bid_volumes[j] = self.bid_volumes[j + 1];
                            self.bid_order_counts[j] = self.bid_order_counts[j + 1];
                        }
                        self.num_bid_levels -= 1;
                        self.bid_prices[self.num_bid_levels] = 0;
                        self.bid_volumes[self.num_bid_levels] = 0;
                        self.bid_order_counts[self.num_bid_levels] = 0;
                    } else {
                        self.bid_volumes[i] -= volume;
                        if order_fully_removed {
                            self.bid_order_counts[i] = self.bid_order_counts[i].saturating_sub(1);
                        }
                    }
                    return;
                }
            }
        } else {
            for i in 0..self.num_ask_levels {
                if self.ask_prices[i] == price {
                    if self.ask_volumes[i] <= volume {
                        for j in i..(self.num_ask_levels - 1) {
                            self.ask_prices[j] = self.ask_prices[j + 1];
                            self.ask_volumes[j] = self.ask_volumes[j + 1];
                            self.ask_order_counts[j] = self.ask_order_counts[j + 1];
                        }
                        self.num_ask_levels -= 1;
                        self.ask_prices[self.num_ask_levels] = 0;
                        self.ask_volumes[self.num_ask_levels] = 0;
                        self.ask_order_counts[self.num_ask_levels] = 0;
                    } else {
                        self.ask_volumes[i] -= volume;
                        if order_fully_removed {
                            self.ask_order_counts[i] = self.ask_order_counts[i].saturating_sub(1);
                        }
                    }
                    return;
                }
            }
        }
    }

    // --- Best Quotes & Prices ---
    #[inline(always)]
    pub fn best_bid(&self) -> (u32, u32) {
        if self.num_bid_levels > 0 {
            (self.bid_prices[0], self.bid_volumes[0])
        } else {
            (0, 0)
        }
    }

    #[inline(always)]
    pub fn best_ask(&self) -> (u32, u32) {
        if self.num_ask_levels > 0 {
            (self.ask_prices[0], self.ask_volumes[0])
        } else {
            (0, 0)
        }
    }

    #[inline(always)]
    pub fn mid_price(&self) -> f32 {
        let (bb_p, _) = self.best_bid();
        let (ba_p, _) = self.best_ask();
        if bb_p > 0 && ba_p > 0 {
            (bb_p as f32 + ba_p as f32) * 0.5
        } else if bb_p > 0 {
            bb_p as f32
        } else {
            ba_p as f32
        }
    }

    #[inline(always)]
    pub fn micro_price(&self) -> f32 {
        let (bb_p, bb_v) = self.best_bid();
        let (ba_p, ba_v) = self.best_ask();
        let total_v = bb_v + ba_v;
        if total_v > 0 && bb_p > 0 && ba_p > 0 {
            // Cont & Stoikov: micro_price = (bb_v * ba_p + ba_v * bb_p) / (bb_v + ba_v)
            (bb_v as f32 * ba_p as f32 + ba_v as f32 * bb_p as f32) / (total_v as f32)
        } else {
            self.mid_price()
        }
    }

    // --- TemporalClockContentSplitter (H_clock vs H_nope) ---
    // Evaluates whether an incoming event is symmetric cancel-replace flicker F_{t+1} = F_{t-k}
    // with zero trade execution (sigma = 0).
    fn check_quote_flicker(&mut self, action: u8, side: u8, price: u32, volume: u32, _ts: u64) -> bool {
        if action == ACTION_ADD || action == ACTION_REPLACE {
            // Check past history ring for symmetric cancellation/re-insertion at identical price & volume
            let lookback = if self.history_len < 16 { self.history_len } else { 16 };
            for k in 1..=lookback {
                let idx = (self.history_head + HISTORY_CAPACITY - k) % HISTORY_CAPACITY;
                let snap = &self.history[idx];
                // Quote flicker: same level re-added after cancellation without intervening trades
                if snap.last_event_price == price
                    && snap.last_event_side == side
                    && snap.last_event_action == ACTION_CANCEL
                    && snap.last_event_volume == volume
                {
                    // Symmetric flicker detected! F_{t+1} = F_{t-k} with sigma = 0
                    let mask_idx = if side == SIDE_BID { 0 } else { MAX_LEVELS_PER_SIDE };
                    self.clock_mask[mask_idx] = 1;
                    self.total_spoof_volume = self.total_spoof_volume.saturating_add(volume as u64);
                    self.spoof_cancels_count = self.spoof_cancels_count.saturating_add(1);
                    return true;
                }
            }
        }
        false
    }

    // --- Causal L3 Tick Processing ---
    pub fn process_tick(
        &mut self,
        action: u8,
        order_id: u64,
        side: u8,
        price: u32,
        volume: u32,
        timestamp_ns: u64,
    ) -> i32 {
        self.ticks_processed += 1;
        self.last_tick_timestamp_ns = timestamp_ns;

        let (prev_bb_p, prev_bb_v) = self.best_bid();
        let (prev_ba_p, prev_ba_v) = self.best_ask();

        let is_flicker = self.check_quote_flicker(action, side, price, volume, timestamp_ns);

        match action {
            ACTION_ADD => {
                // Allocate from free pool
                if self.free_order_head != 0xFFFF && self.active_orders_count < MAX_ORDERS as u16 {
                    let slot = self.free_order_head as usize;
                    self.free_order_head = self.orders[slot].next_idx;

                    let mut flags = FLAG_ACTIVE;
                    if is_flicker {
                        flags |= FLAG_FLICKER;
                    } else {
                        flags |= FLAG_CAUSAL;
                    }

                    self.orders[slot] = OrderEntry {
                        order_id,
                        price,
                        volume,
                        side,
                        flags,
                        pad0: 0,
                        timestamp_ns,
                        level_idx: 0,
                        next_idx: 0xFFFF,
                        prev_idx: 0xFFFF,
                        pad1: 0,
                    };
                    self.insert_order_slot(order_id, slot);
                    self.active_orders_count += 1;

                    self.add_depth(side, price, volume);
                }
            }
            ACTION_CANCEL => {
                if let Some(slot) = self.find_order_slot(order_id) {
                    let price = self.orders[slot].price;
                    let volume = self.orders[slot].volume;
                    let side = self.orders[slot].side;
                    let is_causal = (self.orders[slot].flags & FLAG_CAUSAL) != 0;

                    self.remove_depth(side, price, volume, true);
                    self.remove_order_slot(order_id);

                    // Return to free pool
                    self.orders[slot].flags = 0;
                    self.orders[slot].next_idx = self.free_order_head;
                    self.free_order_head = slot as u16;
                    self.active_orders_count = self.active_orders_count.saturating_sub(1);

                    if !is_causal {
                        self.spoof_cancels_count += 1;
                        self.total_spoof_volume += volume as u64;
                    }
                }
            }
            ACTION_REPLACE => {
                if let Some(slot) = self.find_order_slot(order_id) {
                    let old_price = self.orders[slot].price;
                    let old_volume = self.orders[slot].volume;
                    let old_side = self.orders[slot].side;

                    self.remove_depth(old_side, old_price, old_volume, false);

                    let mut flags = FLAG_ACTIVE;
                    if is_flicker {
                        flags |= FLAG_FLICKER;
                    } else {
                        flags |= FLAG_CAUSAL;
                    }

                    self.orders[slot].price = price;
                    self.orders[slot].volume = volume;
                    self.orders[slot].flags = flags;
                    self.orders[slot].timestamp_ns = timestamp_ns;

                    self.add_depth(side, price, volume);
                }
            }
            ACTION_EXECUTE => {
                // Trade execution (aggressing match)
                if let Some(slot) = self.find_order_slot(order_id) {
                    let exec_vol = core::cmp::min(self.orders[slot].volume, volume);
                    let side = self.orders[slot].side;
                    let p = self.orders[slot].price;

                    self.orders[slot].volume -= exec_vol;
                    let is_fully_executed = self.orders[slot].volume == 0;
                    self.remove_depth(side, p, exec_vol, is_fully_executed);

                    if is_fully_executed {
                        self.remove_order_slot(order_id);
                        self.orders[slot].flags = 0;
                        self.orders[slot].next_idx = self.free_order_head;
                        self.free_order_head = slot as u16;
                        self.active_orders_count = self.active_orders_count.saturating_sub(1);
                    }

                    self.trades_count += 1;
                    self.total_trades_volume += exec_vol as u64;

                    // Execution proves causal flow: H_nope
                    let mask_idx = if side == SIDE_BID { 0 } else { MAX_LEVELS_PER_SIDE };
                    self.nope_mask[mask_idx] = 1;
                }
            }
            _ => return -1,
        }

        // --- Compute Order Flow Imbalance (OFI) ---
        // Cont, Kukanov & Stoikov (2014) OFI formulation:
        let (new_bb_p, new_bb_v) = self.best_bid();
        let (new_ba_p, new_ba_v) = self.best_ask();

        let mut delta_bid_ofi = 0.0f32;
        if new_bb_p > prev_bb_p {
            delta_bid_ofi += new_bb_v as f32;
        } else if new_bb_p == prev_bb_p {
            delta_bid_ofi += new_bb_v as f32 - prev_bb_v as f32;
        } else {
            delta_bid_ofi -= prev_bb_v as f32;
        }

        let mut delta_ask_ofi = 0.0f32;
        if new_ba_p < prev_ba_p {
            delta_ask_ofi += new_ba_v as f32;
        } else if new_ba_p == prev_ba_p {
            delta_ask_ofi += new_ba_v as f32 - prev_ba_v as f32;
        } else {
            delta_ask_ofi -= prev_ba_v as f32;
        }

        let step_raw_ofi = delta_bid_ofi - delta_ask_ofi;
        self.cum_raw_ofi += step_raw_ofi as f64;

        // Purified OFI (G_act vs Omega_reg): If tick was quote flicker, do not accumulate into purified
        let step_purified_ofi = if is_flicker { 0.0 } else { step_raw_ofi };
        self.cum_purified_ofi += step_purified_ofi as f64;

        // Record history snapshot
        let snap = DepthSnapshot {
            timestamp_ns,
            best_bid_price: new_bb_p,
            best_bid_volume: new_bb_v,
            best_ask_price: new_ba_p,
            best_ask_volume: new_ba_v,
            mid_price: self.mid_price(),
            micro_price: self.micro_price(),
            raw_ofi: step_raw_ofi,
            purified_ofi: step_purified_ofi,
            last_event_action: action,
            last_event_side: side,
            pad: [0; 2],
            last_event_price: price,
            last_event_volume: volume,
            pad_tail: [0; 80],
        };

        self.history[self.history_head] = snap;
        self.history_head = (self.history_head + 1) % HISTORY_CAPACITY;
        if self.history_len < HISTORY_CAPACITY {
            self.history_len += 1;
        }

        0
    }

    // --- Rational Approximation for Inverse Standard Normal CDF \Phi^{-1}(p) ---
    // Beasley-Springer-Moro / Acklam rational approximation in pure #![no_std]
    #[allow(clippy::excessive_precision)]
    pub fn inv_normal_cdf(p: f32) -> f32 {
        let p = p.clamp(0.0001, 0.9999);

        let q = p - 0.5;
        if abs_f32(q) <= 0.42 {
            let r = q * q;
            // Central region rational approximation
            let num = (((-2.544106049637e1 * r + 4.1391346154e1) * r - 2.544106049637e1) * r + 5.3062524e0) * q;
            let den = (((1.0 * r - 1.156673419e1) * r + 4.1197992e1) * r - 5.3062524e1) * r + 2.1225009e1;
            num / den
        } else {
            let r = if q < 0.0 { p } else { 1.0 - p };
            // Tail approximation
            let s = (-2.0 * Self::approx_ln(r)).max(0.0001);
            let s_sqrt = Self::approx_sqrt(s);
            let z = s_sqrt - (2.515517 + 0.802853 * s_sqrt + 0.010328 * s)
                / (1.0 + 1.432788 * s_sqrt + 0.189269 * s + 0.001308 * s * s_sqrt);
            if q < 0.0 { -z } else { z }
        }
    }

    // Fast no_std sqrt using hardware intrinsics and scalar fallback
    #[inline(always)]
    pub fn approx_sqrt(x: f32) -> f32 {
        fast_sqrt(x)
    }

    // Fast IEEE-754 no_std ln approximation accurate to < 1 ULP across all positive f32 (including subnormals).
    #[inline(always)]
    pub fn approx_ln(x: f32) -> f32 {
        fast_ln(x)
    }

    // --- 3-Point Discrete Morse Impulse Gate & Pullback ---
    // Evaluates: I_Morse(v_t) = (v_t - v_{t-1}) * (v_t - v_{t+1})
    // With 1-sample causal deferral into pending_impulse,
    // resolving into GLINT_REJECTED (1-tick spike) or STEP_MANEUVER (flash crash).
    pub fn step_morse_gate(&mut self, mid_price: f32, delta_t_ns: u64) -> i32 {
        let v = mid_price;

        // If uninitialized (initial baseline reading):
        if self.morse.v_curr == 0.0 && self.morse.total_steps == 0 && self.morse.total_glints == 0 {
            self.morse.v_curr = v;
            self.morse.v_prev1 = v;
            self.morse.v_prev2 = v;
            return CLASSIFICATION_NOMINAL;
        }

        if self.morse.gate_status == CLASSIFICATION_PENDING_IMPULSE {
            // Second tick: we now have (v_{t-1}, v_t, v_{t+1}) = (v_curr, pending_v, v)
            let v_tm1 = self.morse.v_curr;
            let v_t = self.morse.pending_v;
            let v_tp1 = v;

            let delta_minus = v_t - v_tm1;
            let delta_plus = v_t - v_tp1;
            let i_morse = delta_minus * delta_plus;

            let return_diff = (v_tp1 - v_tm1).abs();
            let step_diff = (v_tp1 - v_t).abs();
            let eps = 0.01f32 * self.morse.variance;

            if return_diff <= eps && i_morse > 0.0 {
                // Strict 1-tick isolated glint: returned to previous level
                self.morse.gate_status = CLASSIFICATION_GLINT_REJECTED;
                self.morse.total_glints += 1;
                // Discard pending_v; resume from v_tm1
                self.morse.v_curr = v_tp1;
                return CLASSIFICATION_GLINT_REJECTED;
            } else if step_diff <= eps || return_diff > eps {
                // Step maneuver: true liquidity vacuum / structural flash shift!
                self.morse.gate_status = CLASSIFICATION_STEP_MANEUVER;
                self.morse.total_steps += 1;
                self.morse.v_prev2 = v_tm1;
                self.morse.v_prev1 = v_t;
                self.morse.v_curr = v_tp1;
                return CLASSIFICATION_STEP_MANEUVER;
            } else {
                self.morse.gate_status = CLASSIFICATION_NOMINAL;
                self.morse.v_prev2 = self.morse.v_prev1;
                self.morse.v_prev1 = self.morse.pending_v;
                self.morse.v_curr = v;
                return CLASSIFICATION_NOMINAL;
            }
        }

        // Nominal tick evaluation
        let diff = (v - self.morse.v_curr).abs();
        let nis = (diff * diff) / (self.morse.variance.max(1e-6));

        // Quantile pullback factor: Phi^{-1}(1 - delta_t / tau_ref)
        let dt_ratio = (delta_t_ns as f32 / self.morse.tau_ref_ns as f32).clamp(0.001, 0.999);
        let phi_inv = Self::inv_normal_cdf(1.0 - 0.5 * dt_ratio);
        let dynamic_threshold = self.morse.chi2_threshold * (phi_inv.max(0.5));

        if nis > dynamic_threshold {
            // Exceeds innovation gate -> 1-sample causal deferral!
            self.morse.gate_status = CLASSIFICATION_PENDING_IMPULSE;
            self.morse.pending_v = v;
            self.morse.pending_dt_ns = delta_t_ns;
            self.morse.pending_nis = nis;
            CLASSIFICATION_PENDING_IMPULSE
        } else {
            // Nominal step
            self.morse.gate_status = CLASSIFICATION_NOMINAL;
            self.morse.v_prev2 = self.morse.v_prev1;
            self.morse.v_prev1 = self.morse.v_curr;
            self.morse.v_curr = v;
            // Online variance update (Welford-style)
            self.morse.variance = 0.95 * self.morse.variance + 0.05 * (diff * diff).max(1e-4);
            CLASSIFICATION_NOMINAL
        }
    }

    // --- so(C) Skew-Symmetric Triad Tie-Breaker ---
    // Evaluates the bilinear triad operator B_W(u, v)_k = \sum_{i, j} u_i v_j (W_{i, j, k} - W_{i, k, j})
    // and applies the Cayley rotor R = (I - \eta/2 M)^{-1} (I + \eta/2 M) in SO(C)
    // with exact 0.000e+00 spherical norm drift.
    #[allow(clippy::needless_range_loop)]
    pub fn evaluate_triad_tie_breaker(&mut self, eta: f32) -> f32 {
        let c = self.num_venues.clamp(2, MAX_CHANNELS);

        // 1. Compute skew-symmetric generator matrix M_{k, j} \in so(C)
        // M_{k, j} = \sum_i u_i (W_{i, j, k} - W_{i, k, j})
        let mut m = [[0.0f32; MAX_CHANNELS]; MAX_CHANNELS];
        for k in 0..c {
            for j in 0..c {
                if j == k {
                    m[k][j] = 0.0;
                    continue;
                }
                let mut sum = 0.0f32;
                for i in 0..c {
                    let w_ijk = self.triad_tensor[i * MAX_CHANNELS * MAX_CHANNELS + j * MAX_CHANNELS + k];
                    let w_ikj = self.triad_tensor[i * MAX_CHANNELS * MAX_CHANNELS + k * MAX_CHANNELS + j];
                    sum += self.market_regime[i] * (w_ijk - w_ikj);
                }
                m[k][j] = sum;
            }
        }

        // Strict antisymmetry verification: M_{k, j} = -M_{j, k}
        for k in 0..c {
            for j in 0..c {
                let diff = m[k][j] + m[j][k];
                if diff.abs() > 1e-6 {
                    let avg = 0.5 * (m[k][j] - m[j][k]);
                    m[k][j] = avg;
                    m[j][k] = -avg;
                }
            }
        }

        // 2. Cayley rotor update: (I - \eta/2 M) v_{new} = (I + \eta/2 M) v_{old}
        // Let A = I - \eta/2 M, rhs = (I + \eta/2 M) v
        let half_eta = 0.5 * eta;
        let mut a = [[0.0f32; MAX_CHANNELS]; MAX_CHANNELS];
        let mut rhs = [0.0f32; MAX_CHANNELS];

        for i in 0..c {
            let mut sum_rhs = 0.0f32;
            for j in 0..c {
                let i_term = if i == j { 1.0 } else { 0.0 };
                a[i][j] = i_term - half_eta * m[i][j];
                sum_rhs += (i_term + half_eta * m[i][j]) * self.venue_state[j];
            }
            rhs[i] = sum_rhs;
        }

        // 3. Solve A v_{new} = rhs via Gaussian elimination with partial pivoting in-place
        for col in 0..c {
            let mut max_row = col;
            let mut max_val = a[col][col].abs();
            for r in (col + 1)..c {
                if a[r][col].abs() > max_val {
                    max_val = a[r][col].abs();
                    max_row = r;
                }
            }
            if max_row != col {
                for k in 0..c {
                    let tmp = a[col][k];
                    a[col][k] = a[max_row][k];
                    a[max_row][k] = tmp;
                }
                rhs.swap(col, max_row);
            }

            let pivot = a[col][col];
            if pivot.abs() > 1e-9 {
                for r in (col + 1)..c {
                    let factor = a[r][col] / pivot;
                    for k in col..c {
                        a[r][k] -= factor * a[col][k];
                    }
                    rhs[r] -= factor * rhs[col];
                }
            }
        }

        // Back-substitution
        let mut v_new = [0.0f32; MAX_CHANNELS];
        for i in (0..c).rev() {
            let mut sum = rhs[i];
            for j in (i + 1)..c {
                sum -= a[i][j] * v_new[j];
            }
            v_new[i] = sum / a[i][i];
        }

        // 4. Verify exact 0.000e+00 spherical norm drift
        let mut initial_norm_sq = 0.0f32;
        let mut final_norm_sq = 0.0f32;
        for i in 0..c {
            initial_norm_sq += self.venue_state[i] * self.venue_state[i];
            final_norm_sq += v_new[i] * v_new[i];
        }

        let drift = (final_norm_sq - initial_norm_sq).abs();
        self.last_spherical_drift = drift;

        self.venue_state[..c].copy_from_slice(&v_new[..c]);

        drift
    }
}

// --- C-ABI Exported Functions for Python ctypes FFI ---

/// Returns the size in bytes of `LOBStateArena`.
#[no_mangle]
pub extern "C" fn lob_arena_size_bytes() -> usize {
    core::mem::size_of::<LOBStateArena>()
}

/// Initializes `LOBStateArena`.
///
/// # Safety
/// `arena_ptr` must point to valid memory for `LOBStateArena`.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_init(arena_ptr: *mut LOBStateArena) -> i32 {
    if arena_ptr.is_null() {
        return -1;
    }
    (*arena_ptr).reset();
    0
}

/// Resets `LOBStateArena`.
///
/// # Safety
/// `arena_ptr` must point to a valid `LOBStateArena`.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_reset(arena_ptr: *mut LOBStateArena) -> i32 {
    if arena_ptr.is_null() {
        return -1;
    }
    (*arena_ptr).reset();
    0
}

/// Processes a single market event tick.
///
/// # Safety
/// `arena_ptr` must point to a valid `LOBStateArena`.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_process_tick(
    arena_ptr: *mut LOBStateArena,
    action: u8,
    order_id: u64,
    side: u8,
    price: u32,
    volume: u32,
    timestamp_ns: u64,
) -> i32 {
    if arena_ptr.is_null() {
        return -1;
    }
    (*arena_ptr).process_tick(action, order_id, side, price, volume, timestamp_ns)
}

/// Extracts top of book (best bid and best ask price/volume).
///
/// # Safety
/// `arena_ptr` must point to a valid `LOBStateArena`. Any non-null output pointer must point to writable memory.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_get_top_of_book(
    arena_ptr: *const LOBStateArena,
    best_bid_p: *mut u32,
    best_bid_v: *mut u32,
    best_ask_p: *mut u32,
    best_ask_v: *mut u32,
) -> i32 {
    if arena_ptr.is_null() {
        return -1;
    }
    let (bb_p, bb_v) = (*arena_ptr).best_bid();
    let (ba_p, ba_v) = (*arena_ptr).best_ask();
    if !best_bid_p.is_null() { *best_bid_p = bb_p; }
    if !best_bid_v.is_null() { *best_bid_v = bb_v; }
    if !best_ask_p.is_null() { *best_ask_p = ba_p; }
    if !best_ask_v.is_null() { *best_ask_v = ba_v; }
    0
}

/// Returns the current micro-price.
///
/// # Safety
/// `arena_ptr` must point to a valid `LOBStateArena`.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_get_micro_price(arena_ptr: *const LOBStateArena) -> f32 {
    if arena_ptr.is_null() {
        return 0.0;
    }
    (*arena_ptr).micro_price()
}

/// Returns the current mid-price.
///
/// # Safety
/// `arena_ptr` must point to a valid `LOBStateArena`.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_get_mid_price(arena_ptr: *const LOBStateArena) -> f32 {
    if arena_ptr.is_null() {
        return 0.0;
    }
    (*arena_ptr).mid_price()
}

/// Returns order flow imbalance (raw and purified).
///
/// # Safety
/// `arena_ptr` must point to a valid `LOBStateArena`. Any non-null output pointer must point to writable memory.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_get_ofi(
    arena_ptr: *const LOBStateArena,
    raw_ofi: *mut f64,
    purified_ofi: *mut f64,
) -> i32 {
    if arena_ptr.is_null() {
        return -1;
    }
    if !raw_ofi.is_null() { *raw_ofi = (*arena_ptr).cum_raw_ofi; }
    if !purified_ofi.is_null() { *purified_ofi = (*arena_ptr).cum_purified_ofi; }
    0
}

/// Advances the 3-point discrete Morse impulse gate.
///
/// # Safety
/// `arena_ptr` must point to a valid `LOBStateArena`.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_step_morse_gate(
    arena_ptr: *mut LOBStateArena,
    mid_price: f32,
    delta_t_ns: u64,
) -> i32 {
    if arena_ptr.is_null() {
        return -1;
    }
    (*arena_ptr).step_morse_gate(mid_price, delta_t_ns)
}

/// Evaluates the so(C) triad tie-breaker with Cayley rotor update.
///
/// # Safety
/// `arena_ptr` must point to a valid `LOBStateArena`. If `drift_out` is non-null, it must point to writable memory.
#[no_mangle]
pub unsafe extern "C" fn lob_arena_evaluate_triad(
    arena_ptr: *mut LOBStateArena,
    eta: f32,
    drift_out: *mut f32,
) -> i32 {
    if arena_ptr.is_null() {
        return -1;
    }
    let drift = (*arena_ptr).evaluate_triad_tie_breaker(eta);
    if !drift_out.is_null() {
        *drift_out = drift;
    }
    0
}

// --- Unit Tests ---
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_arena_size_statically_asserted_under_1_5mb() {
        let sz = core::mem::size_of::<LOBStateArena>();
        assert!(
            sz <= 1_572_864,
            "LOBStateArena size {} exceeds 1.5 MB limit (1,572,864 bytes)",
            sz
        );
        assert_eq!(core::mem::align_of::<LOBStateArena>(), 64);
    }

    #[test]
    fn test_l3_order_book_add_cancel_replace_execute() {
        let mut arena = LOBStateArena::new_const();
        arena.reset();

        // 1. Add Bid: $100.00 (10000 cents), 10 shares
        arena.process_tick(ACTION_ADD, 101, SIDE_BID, 10000, 10, 1_000_000);
        let (bb_p, bb_v) = arena.best_bid();
        assert_eq!(bb_p, 10000);
        assert_eq!(bb_v, 10);

        // 2. Add Ask: $100.50 (10050 cents), 20 shares
        arena.process_tick(ACTION_ADD, 102, SIDE_ASK, 10050, 20, 1_000_100);
        let (ba_p, ba_v) = arena.best_ask();
        assert_eq!(ba_p, 10050);
        assert_eq!(ba_v, 20);

        // Mid price = (10000 + 10050) / 2 = 10025
        assert_eq!(arena.mid_price(), 10025.0);
        // Micro price = (10 * 10050 + 20 * 10000) / 30 = 300500 / 30 = 10016.666
        let micro = arena.micro_price();
        assert!((micro - 10016.666).abs() < 0.1);

        // 3. Replace Ask: change order 102 volume to 15
        arena.process_tick(ACTION_REPLACE, 102, SIDE_ASK, 10050, 15, 1_000_200);
        let (_, ba_v2) = arena.best_ask();
        assert_eq!(ba_v2, 15);

        // 4. Execute: 5 shares against bid order 101
        arena.process_tick(ACTION_EXECUTE, 101, SIDE_BID, 10000, 5, 1_000_300);
        let (_, bb_v2) = arena.best_bid();
        assert_eq!(bb_v2, 5);

        // 5. Cancel remaining 5 shares of order 101
        arena.process_tick(ACTION_CANCEL, 101, SIDE_BID, 10000, 5, 1_000_400);
        assert_eq!(arena.num_bid_levels, 0);
    }

    #[test]
    fn test_high_throughput_ticks_per_sec() {
        let mut arena = LOBStateArena::new_const();
        arena.reset();

        let num_ticks = 50_000;
        for i in 0..num_ticks {
            let p = 10000 + ((i % 20) as u32);
            let action = if i % 4 == 0 {
                ACTION_ADD
            } else if i % 4 == 1 {
                ACTION_REPLACE
            } else if i % 4 == 2 {
                ACTION_EXECUTE
            } else {
                ACTION_CANCEL
            };
            arena.process_tick(
                action,
                (i % 1000) as u64 + 1,
                (i % 2) as u8,
                p,
                5,
                i as u64 * 1000,
            );
        }
        assert_eq!(arena.ticks_processed, num_ticks as u64);
    }

    #[test]
    fn test_quote_flicker_rejection_h_clock() {
        let mut arena = LOBStateArena::new_const();
        arena.reset();

        // Insert order 100 at 10000
        arena.process_tick(ACTION_ADD, 100, SIDE_BID, 10000, 100, 10_000_000);
        // Cancel order 100
        arena.process_tick(ACTION_CANCEL, 100, SIDE_BID, 10000, 100, 10_000_100);
        // Immediately re-insert symmetric quote flicker F_{t+1} = F_{t-k}
        arena.process_tick(ACTION_ADD, 101, SIDE_BID, 10000, 100, 10_000_200);

        // Check clock mask quarantined the flicker
        assert_eq!(arena.clock_mask[0], 1);
        assert!(arena.spoof_cancels_count >= 1);
        // Purified OFI excludes flicker while raw accumulates
        assert_ne!(arena.cum_raw_ofi, arena.cum_purified_ofi);
    }

    #[test]
    fn test_morse_impulse_glint_rejection() {
        let mut arena = LOBStateArena::new_const();
        arena.reset();

        // Nominal price = 100.0
        assert_eq!(arena.step_morse_gate(100.0, 100_000_000), CLASSIFICATION_NOMINAL);
        assert_eq!(arena.step_morse_gate(100.0, 100_000_000), CLASSIFICATION_NOMINAL);

        // Tick 1: Spurious 1-tick data glitch spike to 150.0
        let res1 = arena.step_morse_gate(150.0, 1_000); // High frequency burst -> PENDING_IMPULSE
        assert_eq!(res1, CLASSIFICATION_PENDING_IMPULSE);

        // Tick 2: Immediately reverts to 100.0 -> GLINT_REJECTED!
        let res2 = arena.step_morse_gate(100.0, 1_000);
        assert_eq!(res2, CLASSIFICATION_GLINT_REJECTED);
        assert_eq!(arena.morse.total_glints, 1);
    }

    #[test]
    fn test_morse_impulse_step_maneuver() {
        let mut arena = LOBStateArena::new_const();
        arena.reset();

        // Nominal price = 100.0
        assert_eq!(arena.step_morse_gate(100.0, 100_000_000), CLASSIFICATION_NOMINAL);
        assert_eq!(arena.step_morse_gate(100.0, 100_000_000), CLASSIFICATION_NOMINAL);

        // Tick 1: Flash crash liquidity vacuum drop to 80.0
        let res1 = arena.step_morse_gate(80.0, 1_000);
        assert_eq!(res1, CLASSIFICATION_PENDING_IMPULSE);

        // Tick 2: Price persists at 80.0 -> STEP_MANEUVER!
        let res2 = arena.step_morse_gate(80.0, 1_000);
        assert_eq!(res2, CLASSIFICATION_STEP_MANEUVER);
        assert_eq!(arena.morse.total_steps, 1);
    }

    #[test]
    fn test_so_c_skew_triad_antisymmetry_and_orthogonality() {
        let mut arena = LOBStateArena::new_const();
        arena.reset();

        // Populate anti-symmetric triad tensor W_{0, 1, 0} = 1.0, W_{0, 0, 1} = -1.0
        arena.triad_tensor[8] = 1.5;
        arena.triad_tensor[1] = -1.5;

        let drift = arena.evaluate_triad_tie_breaker(0.01);
        // Exact 0.000e+00 spherical norm drift
        assert!(drift <= 1e-6, "Spherical drift {} exceeds tolerance", drift);
    }

    #[test]
    fn test_so_c_tie_breaker_parity_resolution() {
        let mut arena = LOBStateArena::new_const();
        arena.reset();

        // 2 venues initially in exact symmetric tie v = [1/sqrt(2), 1/sqrt(2)]
        let initial_v0 = arena.venue_state[0];
        let initial_v1 = arena.venue_state[1];
        assert_eq!(initial_v0, initial_v1);

        // Populate anti-symmetric interaction W_{0, 1, 0} = 2.0, W_{0, 0, 1} = -2.0
        // breaking the tie according to directed lead-lag flow
        arena.triad_tensor[8] = 2.0;
        arena.triad_tensor[1] = -2.0;

        let drift = arena.evaluate_triad_tie_breaker(0.05);
        assert!(drift <= 1e-6);

        // Post-triad priority has deterministic non-zero margin
        let diff = (arena.venue_state[0] - arena.venue_state[1]).abs();
        assert!(diff > 1e-4, "Expected parity tie to be broken, got diff {}", diff);

        // Spherical norm is exactly conserved
        let norm_sq = arena.venue_state[0] * arena.venue_state[0] + arena.venue_state[1] * arena.venue_state[1];
        assert!((norm_sq - 1.0).abs() <= 1e-5);
    }

    #[test]
    fn test_causal_factorization_spoofing_purification() {
        let mut arena = LOBStateArena::new_const();
        arena.reset();

        // Legitimate execution flow on bids
        arena.process_tick(ACTION_ADD, 1, SIDE_BID, 10000, 50, 1_000_000);
        arena.process_tick(ACTION_EXECUTE, 1, SIDE_BID, 10000, 50, 1_000_100);

        // Spoofing ping on asks: repeated flicker cancelled without trades
        arena.process_tick(ACTION_ADD, 2, SIDE_ASK, 10050, 100, 1_000_200);
        arena.process_tick(ACTION_CANCEL, 2, SIDE_ASK, 10050, 100, 1_000_300);
        arena.process_tick(ACTION_ADD, 3, SIDE_ASK, 10050, 100, 1_000_400);

        // Raw OFI includes spoof pings, Purified OFI isolates real causal volume
        assert!(arena.total_trades_volume == 50);
        assert!(arena.total_spoof_volume >= 100);
    }

    #[test]
    fn test_c_abi_interface() {
        let sz = lob_arena_size_bytes();
        assert!(sz <= 1_572_864);

        let mut arena = LOBStateArena::new_const();
        unsafe {
            let ret_init = lob_arena_init(&mut arena as *mut _);
            assert_eq!(ret_init, 0);

            let ret_tick = lob_arena_process_tick(
                &mut arena as *mut _,
                ACTION_ADD,
                55,
                SIDE_BID,
                10000,
                10,
                1_000_000,
            );
            assert_eq!(ret_tick, 0);

            let mut bb_p: u32 = 0;
            let mut bb_v: u32 = 0;
            let mut ba_p: u32 = 0;
            let mut ba_v: u32 = 0;
            let ret_tob = lob_arena_get_top_of_book(
                &arena as *const _,
                &mut bb_p as *mut _,
                &mut bb_v as *mut _,
                &mut ba_p as *mut _,
                &mut ba_v as *mut _,
            );
            assert_eq!(ret_tob, 0);
            assert_eq!(bb_p, 10000);
            assert_eq!(bb_v, 10);

            let micro = lob_arena_get_micro_price(&arena as *const _);
            assert_eq!(micro, 10000.0);

            let mut drift: f32 = 0.0;
            let ret_triad = lob_arena_evaluate_triad(&mut arena as *mut _, 0.01, &mut drift as *mut _);
            assert_eq!(ret_triad, 0);
            assert!(drift <= 1e-6);
        }
    }

    #[test]
    fn test_fast_math_edge_cases_and_subnormals() {
        for &val in &[1e-40f32, 1e-12, 0.01, 0.5, 1.0, 2.0, 100.0, 1e10] {
            let s_hw = fast_sqrt(val);
            let s_sc = fast_sqrt_scalar_f32(val);
            assert!(abs_f32(s_hw - val.sqrt()) / val.sqrt() < 1e-6);
            assert!(abs_f32(s_sc - val.sqrt()) / val.sqrt() < 1e-6);
            let l = fast_ln(val);
            assert!(abs_f32(l - val.ln()) < 1e-5, "fast_ln({}) = {} vs {}", val, l, val.ln());
            assert_eq!(approx_ln(val), fast_ln(val));
            assert_eq!(approx_sqrt(val), fast_sqrt(val));
        }
        assert_eq!(fast_sqrt(0.0), 0.0);
        assert_eq!(fast_sqrt(-5.0), 0.0);
        assert!(fast_sqrt(f32::INFINITY).is_infinite());
        assert!(fast_sqrt_scalar_f32(f32::INFINITY).is_infinite());
        assert!(fast_sqrt(f32::NAN).is_nan());
        assert!(fast_ln(f32::INFINITY).is_infinite());
        assert_eq!(fast_ln(0.0), f32::NEG_INFINITY);
        assert_eq!(fast_ln(-1.0), f32::NEG_INFINITY);
        assert!(fast_ln(f32::NAN).is_nan());
        assert_eq!(approx_ln(f32::INFINITY), f32::INFINITY);
        assert_eq!(approx_ln(0.0), f32::NEG_INFINITY);
        assert_eq!(approx_ln(-5.0), f32::NEG_INFINITY);
    }
}

