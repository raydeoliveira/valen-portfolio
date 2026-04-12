"""Volume-Synchronized Probability of Informed Trading (VPIN) calculator.

VPIN measures order flow toxicity — the probability that informed traders
are adversely selecting market makers. This is a Layer 2 execution gate:
it does NOT generate directional signals. High VPIN means "bad time to
execute a market order" (wide spreads, adverse fills likely).

Algorithm (Easley, López de Prado, O'Hara 2012):
1. Partition trades into equal-volume buckets.
2. Classify each bucket as buy/sell using Bulk Volume Classification (BVC):
   sign(close - open) of the bucket determines the dominant side.
3. VPIN = rolling mean of |V_buy - V_sell| / V_bucket over N buckets.

Output: toxicity score in [0, 1].
  0.0 = perfectly balanced flow (no toxicity)
  1.0 = completely one-sided flow (maximum toxicity)
"""

from __future__ import annotations

import logging
import sqlite3
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.adapters.db_factory import get_service_connection

log = logging.getLogger("valen.execution.vpin")

# ── Defaults ──────────────────────────────────────────────────────────
DEFAULT_DB_PATH = "data/trades_tick.db"
DEFAULT_BUCKET_VOLUME: float = 1.0  # BTC-equivalent volume per bucket
DEFAULT_N_BUCKETS: int = 50  # rolling window for VPIN

# Per-asset bucket volume calibration.
# BTC trades are ~$70K per unit -> 1.0 BTC = ~$70K notional per bucket.
# For smaller-priced assets, calibrate to roughly the same notional range.
# Key: approximate $50K-$100K notional per bucket.
ASSET_BUCKET_VOLUME: dict[str, float] = {
    "BTC": 1.0,  # ~$70K per bucket
    "ETH": 20.0,  # ~$70K per bucket at ~$3500/ETH
    "SOL": 400.0,  # ~$60K per bucket at ~$150/SOL
    "HYPE": 2500.0,  # ~$50K per bucket at ~$20/HYPE
    "SUI": 20000.0,  # ~$60K per bucket at ~$3/SUI
    "AVAX": 2000.0,  # ~$60K per bucket at ~$30/AVAX
    "LINK": 3500.0,  # ~$56K per bucket at ~$16/LINK
    "DOGE": 300000.0,  # ~$54K per bucket at ~$0.18/DOGE
}
MIN_BUCKETS_FOR_SIGNAL: int = 10  # minimum buckets before emitting a value
CACHE_TTL_SECONDS: float = 1.0
DB_BUSY_TIMEOUT_MS: int = 30_000


class ToxicityLevel(str, Enum):
    """Toxicity regime classification."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


# Thresholds calibrated from academic literature (Easley et al. 2012)
# and typical crypto microstructure: crypto markets are structurally
# more toxic than equities, so thresholds are higher.
DEFAULT_TOXICITY_THRESHOLDS: dict[ToxicityLevel, float] = {
    ToxicityLevel.LOW: 0.30,
    ToxicityLevel.MODERATE: 0.50,
    ToxicityLevel.HIGH: 0.70,
}


class ExecutionRecommendation(str, Enum):
    """Execution recommendation based on VPIN toxicity."""

    PROCEED = "PROCEED"
    USE_LIMIT_ONLY = "USE_LIMIT_ONLY"
    DELAY = "DELAY"
    HALT = "HALT"


@dataclass(frozen=True)
class VolumeBucket:
    """A single equal-volume bucket of trades."""

    open_px: float
    close_px: float
    high_px: float
    low_px: float
    total_volume: float
    buy_volume: float  # BVC-classified
    sell_volume: float  # BVC-classified
    n_trades: int
    ts_start_ms: int
    ts_end_ms: int


@dataclass(frozen=True)
class VPINResult:
    """VPIN computation result."""

    vpin: float  # 0-1 toxicity score
    toxicity_level: ToxicityLevel
    recommendation: ExecutionRecommendation
    n_buckets: int
    bucket_volume: float
    stale: bool
    reason: str


@dataclass
class _BucketAccumulator:
    """Accumulates trades into a volume bucket in progress."""

    target_volume: float
    volume_so_far: float = 0.0
    open_px: float = 0.0
    close_px: float = 0.0
    high_px: float = -1e18
    low_px: float = 1e18
    n_trades: int = 0
    ts_start_ms: int = 0
    ts_end_ms: int = 0

    def add_trade(self, px: float, sz: float, ts_ms: int) -> None:
        """Add a single trade to the accumulator."""
        if self.n_trades == 0:
            self.open_px = px
            self.ts_start_ms = ts_ms
        self.close_px = px
        self.high_px = max(self.high_px, px)
        self.low_px = min(self.low_px, px)
        self.volume_so_far += sz
        self.n_trades += 1
        self.ts_end_ms = ts_ms

    @property
    def is_full(self) -> bool:
        return self.volume_so_far >= self.target_volume

    def to_bucket(self) -> VolumeBucket:
        """Finalize into an immutable VolumeBucket with BVC classification."""
        # Bulk Volume Classification: sign of price change determines
        # whether the bucket volume is classified as buy or sell.
        price_change = self.close_px - self.open_px
        if price_change > 0:
            buy_volume = self.volume_so_far
            sell_volume = 0.0
        elif price_change < 0:
            buy_volume = 0.0
            sell_volume = self.volume_so_far
        else:
            # No price change: split 50/50
            buy_volume = self.volume_so_far / 2.0
            sell_volume = self.volume_so_far / 2.0

        return VolumeBucket(
            open_px=self.open_px,
            close_px=self.close_px,
            high_px=self.high_px,
            low_px=self.low_px,
            total_volume=self.volume_so_far,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            n_trades=self.n_trades,
            ts_start_ms=self.ts_start_ms,
            ts_end_ms=self.ts_end_ms,
        )

    def reset(self) -> None:
        """Reset for next bucket, keeping target_volume."""
        self.volume_so_far = 0.0
        self.open_px = 0.0
        self.close_px = 0.0
        self.high_px = -1e18
        self.low_px = 1e18
        self.n_trades = 0
        self.ts_start_ms = 0
        self.ts_end_ms = 0


class VPINCalculator:
    """Computes VPIN (Volume-Synchronized Probability of Informed Trading).

    Usage:
        calc = VPINCalculator(bucket_volume=1.0, n_buckets=50)

        # Option 1: from live trade stream
        for trade in stream:
            calc.update(trade.px, trade.sz, trade.ts_ms)
        result = calc.current_vpin()

        # Option 2: from database
        result = calc.compute_from_db("BTC")
    """

    def __init__(
        self,
        bucket_volume: float = DEFAULT_BUCKET_VOLUME,
        n_buckets: int = DEFAULT_N_BUCKETS,
        toxicity_thresholds: dict[ToxicityLevel, float] | None = None,
        db_path: str = DEFAULT_DB_PATH,
    ) -> None:
        self._bucket_volume = bucket_volume
        self._n_buckets = n_buckets
        self._thresholds = toxicity_thresholds or dict(
            DEFAULT_TOXICITY_THRESHOLDS
        )
        self._db_path = db_path

        # Rolling window of completed buckets
        self._buckets: deque[VolumeBucket] = deque(maxlen=n_buckets)
        # In-progress bucket accumulator
        self._acc = _BucketAccumulator(target_volume=bucket_volume)
        # Cache for DB-based computation
        self._cache: dict[str, tuple[float, VPINResult]] = {}

        log.info(
            "VPINCalculator init: bucket_vol=%.4f, n_buckets=%d",
            bucket_volume,
            n_buckets,
        )

    # ── Public: streaming interface ───────────────────────────────────

    def update(self, px: float, sz: float, ts_ms: int) -> VolumeBucket | None:
        """Feed a single trade. Returns a VolumeBucket if one was completed."""
        if px <= 0 or sz <= 0:
            return None

        remaining = sz
        completed_bucket: VolumeBucket | None = None

        while remaining > 0:
            space = self._acc.target_volume - self._acc.volume_so_far
            fill = min(remaining, space)
            self._acc.add_trade(px, fill, ts_ms)
            remaining -= fill

            if self._acc.is_full:
                bucket = self._acc.to_bucket()
                self._buckets.append(bucket)
                completed_bucket = bucket
                self._acc.reset()

        return completed_bucket

    def current_vpin(self) -> VPINResult:
        """Compute VPIN from the current rolling bucket window."""
        n = len(self._buckets)
        if n < MIN_BUCKETS_FOR_SIGNAL:
            return VPINResult(
                vpin=0.0,
                toxicity_level=ToxicityLevel.LOW,
                recommendation=ExecutionRecommendation.PROCEED,
                n_buckets=n,
                bucket_volume=self._bucket_volume,
                stale=True,
                reason=f"Insufficient buckets ({n}/{MIN_BUCKETS_FOR_SIGNAL})",
            )

        vpin = self._compute_vpin_from_buckets(list(self._buckets))
        level = self._classify(vpin)
        rec = self._recommend(level)
        return VPINResult(
            vpin=vpin,
            toxicity_level=level,
            recommendation=rec,
            n_buckets=n,
            bucket_volume=self._bucket_volume,
            stale=False,
            reason=f"VPIN={vpin:.4f} over {n} buckets",
        )

    def reset(self) -> None:
        """Clear all state."""
        self._buckets.clear()
        self._acc.reset()
        self._cache.clear()

    # ── Public: database interface ────────────────────────────────────

    def compute_from_db(
        self,
        coin: str,
        db_path: str | None = None,
        lookback_trades: int = 50_000,
    ) -> VPINResult:
        """Compute VPIN for a coin from trades_tick.db.

        Args:
            coin: Coin symbol (e.g. "BTC").
            db_path: Override database path.
            lookback_trades: Number of recent trades to use.
        """
        now = time.monotonic()
        cached = self._cache.get(coin)
        if cached and (now - cached[0]) < CACHE_TTL_SECONDS:
            return cached[1]

        path = Path(db_path or self._db_path)
        if not path.exists():
            result = VPINResult(
                vpin=0.0,
                toxicity_level=ToxicityLevel.LOW,
                recommendation=ExecutionRecommendation.PROCEED,
                n_buckets=0,
                bucket_volume=self._bucket_volume,
                stale=True,
                reason=f"DB not found: {path}",
            )
            self._cache[coin] = (now, result)
            return result

        try:
            trades = self._fetch_trades(path, coin, lookback_trades)
        except sqlite3.Error:
            log.exception("Failed to query trades_tick.db for %s", coin)
            result = VPINResult(
                vpin=0.0,
                toxicity_level=ToxicityLevel.LOW,
                recommendation=ExecutionRecommendation.PROCEED,
                n_buckets=0,
                bucket_volume=self._bucket_volume,
                stale=True,
                reason="DB query failed",
            )
            self._cache[coin] = (now, result)
            return result

        if not trades:
            result = VPINResult(
                vpin=0.0,
                toxicity_level=ToxicityLevel.LOW,
                recommendation=ExecutionRecommendation.PROCEED,
                n_buckets=0,
                bucket_volume=self._bucket_volume,
                stale=True,
                reason=f"No trades for {coin}",
            )
            self._cache[coin] = (now, result)
            return result

        # Use per-asset calibration if available and user didn't override
        effective_bucket_vol = self._bucket_volume
        if (
            self._bucket_volume == DEFAULT_BUCKET_VOLUME
            and coin in ASSET_BUCKET_VOLUME
        ):
            effective_bucket_vol = ASSET_BUCKET_VOLUME[coin]

        buckets = self.volume_bucket(trades, effective_bucket_vol)
        if len(buckets) < MIN_BUCKETS_FOR_SIGNAL:
            result = VPINResult(
                vpin=0.0,
                toxicity_level=ToxicityLevel.LOW,
                recommendation=ExecutionRecommendation.PROCEED,
                n_buckets=len(buckets),
                bucket_volume=effective_bucket_vol,
                stale=True,
                reason=f"Insufficient buckets ({len(buckets)}/{MIN_BUCKETS_FOR_SIGNAL})",
            )
            self._cache[coin] = (now, result)
            return result

        # Use the last N buckets
        window = buckets[-self._n_buckets :]
        vpin = self._compute_vpin_from_buckets(window)
        level = self._classify(vpin)
        rec = self._recommend(level)
        result = VPINResult(
            vpin=vpin,
            toxicity_level=level,
            recommendation=rec,
            n_buckets=len(window),
            bucket_volume=effective_bucket_vol,
            stale=False,
            reason=f"VPIN={vpin:.4f} from {len(trades)} trades, {len(window)} buckets",
        )
        self._cache[coin] = (now, result)
        return result

    # ── Public: static helpers ────────────────────────────────────────

    @staticmethod
    def volume_bucket(
        trades: list[tuple[float, float, int]],
        bucket_volume: float,
    ) -> list[VolumeBucket]:
        """Split a list of (px, sz, ts_ms) trades into equal-volume buckets.

        This is the pure-function version for backtesting / analysis.
        """
        acc = _BucketAccumulator(target_volume=bucket_volume)
        buckets: list[VolumeBucket] = []

        for px, sz, ts_ms in trades:
            if px <= 0 or sz <= 0:
                continue
            remaining = sz
            while remaining > 0:
                space = acc.target_volume - acc.volume_so_far
                fill = min(remaining, space)
                acc.add_trade(px, fill, ts_ms)
                remaining -= fill
                if acc.is_full:
                    buckets.append(acc.to_bucket())
                    acc.reset()

        return buckets

    @staticmethod
    def classify_trades(buckets: list[VolumeBucket]) -> list[VolumeBucket]:
        """Classify buckets using BVC (already done in to_bucket). Identity op.

        Provided for API completeness — BVC is applied at bucket creation.
        """
        return buckets

    @staticmethod
    def compute_vpin(
        buckets: list[VolumeBucket], n_buckets: int = DEFAULT_N_BUCKETS
    ) -> float:
        """Compute VPIN over the last n_buckets.

        Returns 0-1 toxicity score. Returns 0.0 if insufficient data.
        """
        if len(buckets) < MIN_BUCKETS_FOR_SIGNAL:
            return 0.0
        window = buckets[-n_buckets:]
        return VPINCalculator._compute_vpin_from_buckets(window)

    @staticmethod
    def get_bucket_volume(coin: str) -> float:
        """Return calibrated bucket volume for *coin*."""
        return ASSET_BUCKET_VOLUME.get(coin, DEFAULT_BUCKET_VOLUME)

    # ── Private ───────────────────────────────────────────────────────

    @staticmethod
    def _compute_vpin_from_buckets(buckets: list[VolumeBucket]) -> float:
        """Core VPIN formula: mean(|V_buy - V_sell| / V_total) over buckets."""
        if not buckets:
            return 0.0
        imbalances: list[float] = []
        for b in buckets:
            if b.total_volume > 0:
                imbalances.append(
                    abs(b.buy_volume - b.sell_volume) / b.total_volume
                )
        if not imbalances:
            return 0.0
        return sum(imbalances) / len(imbalances)

    def _classify(self, vpin: float) -> ToxicityLevel:
        """Classify VPIN into toxicity regime."""
        if vpin < self._thresholds[ToxicityLevel.LOW]:
            return ToxicityLevel.LOW
        if vpin < self._thresholds[ToxicityLevel.MODERATE]:
            return ToxicityLevel.MODERATE
        if vpin < self._thresholds[ToxicityLevel.HIGH]:
            return ToxicityLevel.HIGH
        return ToxicityLevel.EXTREME

    @staticmethod
    def _recommend(level: ToxicityLevel) -> ExecutionRecommendation:
        """Map toxicity level to execution recommendation."""
        mapping = {
            ToxicityLevel.LOW: ExecutionRecommendation.PROCEED,
            ToxicityLevel.MODERATE: ExecutionRecommendation.USE_LIMIT_ONLY,
            ToxicityLevel.HIGH: ExecutionRecommendation.DELAY,
            ToxicityLevel.EXTREME: ExecutionRecommendation.HALT,
        }
        return mapping[level]

    def _fetch_trades(
        self, db_path: Path, coin: str, limit: int
    ) -> list[tuple[float, float, int]]:
        """Fetch recent trades from trades_tick.db."""
        conn = get_service_connection(
            db_path,
            readonly=True,
            busy_timeout_ms=DB_BUSY_TIMEOUT_MS,
        )
        try:
            rows = conn.execute(
                "SELECT px, sz, ts_ms FROM trades "
                "WHERE coin = ? ORDER BY ts_ms DESC LIMIT ?",
                (coin, limit),
            ).fetchall()
        finally:
            conn.close()

        # Reverse to chronological order
        rows.reverse()
        return [(float(r[0]), float(r[1]), int(r[2])) for r in rows]

    def _bucketize_trades(
        self, trades: list[tuple[float, float, int]]
    ) -> list[VolumeBucket]:
        """Convert a list of trades into equal-volume buckets."""
        return self.volume_bucket(trades, self._bucket_volume)
