import os
import math
from simular import PyEvm

from usdc_weth_model import abis

Q96 = 2**96
TICK_BASE = 1.0001

"""
Tick spacing by fee
 Fee%     spacing
 ----------------
 0.01        1
 0.05        10
 0.3         60
 1.0         200
"""


def price_to_sqrtp(p):
    return int(math.sqrt(p) * Q96)


def sqrtp_to_price(sqrtp):
    """Given sqrtp from slot0 return the price"""
    return (sqrtp / Q96) ** 2


def token1_price(sqrtp):
    """Calculate the price of token0"""
    sp = sqrtp_to_price(sqrtp)
    return sp / 1e12


def token0_price(sqrtp):
    """Calculate the price of token1"""
    t0 = token1_price(sqrtp)
    return 1 / t0


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


def x_harcoded():
    L = 22402462192838616433
    P = 3211.84
    # tick bottom
    pa = tick_to_price(195540)
    # tick top
    pb = tick_to_price(195600)
    print(pb)

    x = L * (math.sqrt(pb) - math.sqrt(P) / math.sqrt(P) * math.sqrt(pb))
    print(x)


def x_liq(p, pb, L):
    return L * ((math.sqrt(pb) - p) / (p * math.sqrt(pb)))


def y_liq(p, pa, L):
    return L * (p - math.sqrt(pa))


def try_latest():
    FEE = 500
    tick_space = 10

    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    factory_contract = abis.uniswap_factory_contract(evm)
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, FEE)
    pool = abis.uniswap_pool_contract(evm, pool_address)
    slot0 = pool.slot0.call()

    P = slot0[0]
    current_tick = slot0[1]
    L = pool.liquidity.call()

    tb, tt = get_tick_range(current_tick, tick_space)
    print(f"tick range ({tb} - {tt})")
    pa = tick_to_price(tb)
    pb = tick_to_price(tt)

    p_prime = P / Q96

    x = x_liq(p_prime, pb, L)
    y = y_liq(p_prime, pa, L)

    xadj = x
    yadj = y

    print(f"{xadj/1e6} USDC in this range")
    print(f"{yadj/1e18} ETH in this range")


if __name__ == "__main__":
    try_latest()
