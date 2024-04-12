import math
import numpy as np


Q96 = 2**96
TICK_BASE = 1.0001


def sqrtp_to_price(sqrtp):
    """Given sqrtp from slot0 return the price"""
    return (sqrtp / Q96) ** 2


def token0_price(sqrtp):
    """Calculate the price USDC for 1 ETH"""
    t0 = token1_price(sqrtp)
    return 1 / t0


def token1_price(sqrtp):
    """Calculate the price of weth for 1 USDC"""
    sp = sqrtp_to_price(sqrtp)
    return sp / 1e12


def tick_to_sqrtpx96(tick: int) -> int:
    """get the sqrt price from the tick
    Below is the same as:
    sqrt(1.0001**tick)
    """
    # sqrt_pricex96 = (1.0001 ** (tick / 2)) * Q96
    # return int(sqrt_pricex96)
    return np.sqrt(1.0001**tick) * 2**96


def get_lower_tick(tick, spacing):
    """get lower tick by current tick and spacing"""
    return math.floor(tick / spacing) * spacing


def get_upper_tick(tick, spacing):
    """get upper tick by current tick and spacing"""
    lt = get_lower_tick(tick, spacing)
    return lt + spacing


def get_tick_range(current_tick, spacing):
    """get tick range by current tick and spacing"""
    lt = get_lower_tick(current_tick, spacing)
    ut = lt + spacing
    return (lt, ut)


def tick_to_price(tick):
    """get price by tick"""
    return TICK_BASE**tick


def x_liq(p, pb, L):
    """get the liquidity of token0 (x)"""
    return L * ((math.sqrt(pb) - p) / (p * math.sqrt(pb)))


def y_liq(p, pa, L):
    """get the liquidity of token1 (y)"""
    return L * (p - math.sqrt(pa))
