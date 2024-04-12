"""
Experiment: 
Sweep a tick range based on the number of steps.
Get a target price from the tick
Compare to the current price
View liquidity
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import root_scalar

from simular import PyEvm

from uniswap_demo import abis
from uniswap_demo.uniswap_math import tick_to_sqrtpx96, Q96


def amountin(liq, target, current):
    change = target - current
    return int(liq * change / Q96)


def sweep(evm, num_steps: int = 10):
    factory_contract = abis.uniswap_factory_contract(evm)
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, abis.FEE)
    pool = abis.uniswap_pool_contract(evm, pool_address)

    slot0 = pool.slot0.call()
    current_price = slot0[0]
    current_tick = slot0[1]

    liquidity = pool.liquidity.call()

    print(f"start tick: {current_tick}")
    ticks = [current_tick + (i * abis.TICK_SPACING) for i in range(num_steps // 2)]
    ticks.extend(
        [current_tick + (i * abis.TICK_SPACING) for i in range(num_steps // 2)]
    )
    print(ticks)

    print(f"current price: {current_price}")
    for i in range(num_steps):
        tick = ticks[i]
        tp = tick_to_sqrtpx96(tick)
        print(f"tick: {tick}")
        amt = amountin(liquidity, tp, current_price)
        print(f"amount: {amt}")


def simulate_snapshot_agent(evm, num_steps=10):
    factory_contract = abis.uniswap_factory_contract(evm)
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, abis.FEE)
    pool = abis.uniswap_pool_contract(evm, pool_address)
    router = abis.uniswap_router_contract(evm)
    quoter = abis.uniswap_quoter_contract(evm)

    token0 = pool.token0.call()
    token1 = pool.token1.call()

    current_tick = pool.slot0.call()[1]
    ticks = [current_tick + (i * abis.TICK_SPACING) for i in range(num_steps // 2)]
    ticks.extend(
        [current_tick + (i * abis.TICK_SPACING) for i in range(num_steps // 2)]
    )

    # steps
    for i in range(num_steps):
        tick = ticks[i]
        sqrt_target_price_x96 = tick_to_sqrtpx96(tick)

        sqrt_current_price_x96 = pool.slot0.call()[0]
        liquidity = pool.liquidity.call()

        if sqrt_target_price_x96 > sqrt_current_price_x96:
            # buy usdc w/eth
            change_sqrt_price_x96 = sqrt_target_price_x96 - sqrt_current_price_x96
            change_token_1 = int(liquidity * change_sqrt_price_x96 / 2**96)
            if change_token_1 == 0:
                continue

            # look for the closet matching anount to match
            def _quote_price(change_token_1):
                return quoter.quoteExactInputSingle.call(
                    token1, token0, abis.FEE, int(change_token_1), 0
                )

            try:
                sol = root_scalar(
                    lambda x: _quote_price(x) - sqrt_target_price_x96,
                    x0=change_token_1 // 2,
                    method="newton",
                    maxiter=5,
                )
                change_token_1 = sol.root
            except:
                return None

            swapped = router.exactInputSingle.transact(
                (
                    token1,
                    token0,
                    abis.FEE,
                    self.address,
                    int(1e32),
                    int(amountin),
                    0,
                    0,
                ),
                caller=self.address,
            )

        else:
            # buy eth w/usdc (1e6)
            pass


def quoter(evm, token_in, token_out, amount):
    quote = abis.uniswap_quoter_contract(evm)
    return quote.quoteExactInputSingle.call(
        token_in, token_out, abis.FEE, int(amount), 0
    )


def do_quote(evm, amount):
    """
    Swap ETH for USDC: amount in is in WEI 1e18

    SWAP USDC to ETH: amount in is in USDC 1e6
    """
    factory_contract = abis.uniswap_factory_contract(evm)
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, abis.FEE)
    pool = abis.uniswap_pool_contract(evm, pool_address)

    token0 = pool.token0.call()
    token1 = pool.token1.call()
    result = quoter(evm, token0, token1, amount)

    print(f"{result}")


def gbm(rng, token_a_price, mu=0.1, sigma=0.2, dt=0.01, price_imact=0.2):
    """Basic geometric brownian motion"""
    z = rng.normal()
    return token_a_price * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z)


if __name__ == "__main__":
    # evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    # sweep(evm)

    # do_quote(evm, 3511 * 1e6)

    rng = np.random.default_rng()
    price = 3500.012
    all = [price]
    for i in range(500):
        price = gbm(rng, price)
        all.append(price)

    plt.xlabel("Steps")
    plt.ylabel("USDC per ETH")
    plt.plot(all)
    plt.show()
