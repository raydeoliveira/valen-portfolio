"""VALEN Canonical Fee Model — realistic Hyperliquid fee tiers.

ALL backtests MUST use this module for fee calculations. Never hardcode
fee rates in scripts — import from here instead. (Rule 37)

Hyperliquid uses a volume-based tiered fee schedule. Maker orders receive
lower fees (and potential rebates at high tiers). Taker orders are more
expensive. A referral discount (set_referrer, 4%) is applied by default.

Key rules:
  - Real trades (entry/exit) incur taker or maker fees.
  - Leverage changes (update_leverage) are ALWAYS ZERO fee.
  - Margin adjustments (updateIsolatedMargin) are ALWAYS ZERO fee.
  - The 4% set_referrer discount applies to all trade fees.

Usage (class-based, for BacktestEngine/PortfolioEngine):
    from src.backtesting.fee_model import FeeModel
    model = FeeModel(referral_discount=REFERRAL_DISCOUNT)
    fee = model.calculate_fee(size, price, is_maker=False)

Usage (function-based, for ad-hoc scripts):
    from src.backtesting.fee_model import (
        compute_trade_fee, compute_leverage_change_fee,
        EFFECTIVE_TAKER_RATE, EFFECTIVE_MAKER_RATE,
    )
    fee = compute_trade_fee(notional_usd)       # real trade
    fee = compute_leverage_change_fee(notional)  # always 0.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

log = logging.getLogger("valen")

# ---------------------------------------------------------------------------
# Canonical HL fee constants (VIP 0 — our tier as of 2026-03)
# ---------------------------------------------------------------------------

# Base rates in basis points
HL_TAKER_BPS: float = 4.5   # 0.045%
HL_MAKER_BPS: float = 1.5   # 0.015%

# set_referrer discount (4% — must be activated via API call)
REFERRAL_DISCOUNT: Decimal = Decimal("0.04")
REFERRAL_DISCOUNT_FLOAT: float = 0.04

# Effective rates after 4% referral discount
EFFECTIVE_TAKER_BPS: float = HL_TAKER_BPS * (1 - REFERRAL_DISCOUNT_FLOAT)   # 4.32 bps
EFFECTIVE_MAKER_BPS: float = HL_MAKER_BPS * (1 - REFERRAL_DISCOUNT_FLOAT)   # 1.44 bps
EFFECTIVE_TAKER_RATE: float = EFFECTIVE_TAKER_BPS / 10_000                   # 0.000432
EFFECTIVE_MAKER_RATE: float = EFFECTIVE_MAKER_BPS / 10_000                   # 0.000144


# ---------------------------------------------------------------------------
# Convenience functions for ad-hoc scripts
# ---------------------------------------------------------------------------

def compute_trade_fee(
    notional_usd: float,
    order_type: str = "MARKET",
) -> float:
    """Fee for a real trade (entry or exit).

    Args:
        notional_usd: Absolute notional value of the trade in USD.
        order_type: "MARKET" (taker) or "ALO" (maker/limit).

    Returns:
        Fee in USD.
    """
    if order_type == "ALO":
        return notional_usd * EFFECTIVE_MAKER_RATE
    return notional_usd * EFFECTIVE_TAKER_RATE


def compute_leverage_change_fee(notional_usd: float) -> float:
    """Fee for update_leverage() — ALWAYS ZERO on Hyperliquid."""
    return 0.0


def compute_margin_adjustment_fee(amount_usd: float) -> float:
    """Fee for updateIsolatedMargin() — ALWAYS ZERO on Hyperliquid."""
    return 0.0


def _check_fee_model(
    taker_rate: float | None = None,
    maker_rate: float | None = None,
    *,
    tolerance: float = 1e-6,
) -> list[str]:
    """Validate that a backtest is using the canonical fee model.

    Call this at the start of every backtest script to ensure no hardcoded
    rates have drifted from the canonical values.

    Returns:
        List of warning strings. Empty means all checks passed.
    """
    warnings: list[str] = []

    if taker_rate is not None:
        diff = abs(taker_rate - EFFECTIVE_TAKER_RATE)
        if diff > tolerance:
            warnings.append(
                f"Taker rate {taker_rate:.6f} differs from canonical "
                f"{EFFECTIVE_TAKER_RATE:.6f} (diff={diff:.8f}). "
                f"Import EFFECTIVE_TAKER_RATE from src.backtesting.fee_model."
            )

    if maker_rate is not None:
        diff = abs(maker_rate - EFFECTIVE_MAKER_RATE)
        if diff > tolerance:
            warnings.append(
                f"Maker rate {maker_rate:.6f} differs from canonical "
                f"{EFFECTIVE_MAKER_RATE:.6f} (diff={diff:.8f}). "
                f"Import EFFECTIVE_MAKER_RATE from src.backtesting.fee_model."
            )

    return warnings


# ---------------------------------------------------------------------------
# Class-based interface (for BacktestEngine / PortfolioEngine)
# ---------------------------------------------------------------------------

@dataclass
class FeeModel:
    """Canonical Hyperliquid fee model for backtesting.

    Encapsulates the fee schedule so that backtest engines don't need
    to know about HL-specific rate tiers.
    """

    referral_discount: Decimal = REFERRAL_DISCOUNT

    @property
    def taker_rate(self) -> float:
        return HL_TAKER_BPS / 10_000 * (1 - float(self.referral_discount))

    @property
    def maker_rate(self) -> float:
        return HL_MAKER_BPS / 10_000 * (1 - float(self.referral_discount))

    def calculate_fee(
        self,
        size: float,
        price: float,
        is_maker: bool = False,
    ) -> float:
        """Calculate fee for a trade.

        Args:
            size: Position size in base asset units.
            price: Execution price.
            is_maker: True for ALO/limit fills, False for market/taker.

        Returns:
            Fee in USDC.
        """
        notional = abs(size * price)
        rate = self.maker_rate if is_maker else self.taker_rate
        return notional * rate

    def leverage_change_fee(self) -> float:
        """Leverage changes are ZERO fee on Hyperliquid."""
        return 0.0
