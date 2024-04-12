"""
Take a snapshot of on-chain state
"""

import os
from simular import create_account, PyEvm
from uniswap_demo import abis
from uniswap_demo.model import UniswapModel, USDC_DEPOSIT
from uniswap_demo.agent import SnapShotAgent

from uniswap_demo import uniswap_math

MINTER_ALLOWANCE = USDC_DEPOSIT


def setup_usdc(evm):
    usdc = abis.usdc_contract(evm)
    master_minter = usdc.masterMinter.call()

    # Create a minter account
    create_account(evm, address=abis.USDC_MINTER)
    create_account(evm, address=master_minter)

    # grant minter status
    usdc.configureMinter.transact(
        abis.USDC_MINTER, MINTER_ALLOWANCE, caller=master_minter
    )
    # mint to self
    usdc.mint.transact(abis.USDC_MINTER, MINTER_ALLOWANCE, caller=abis.USDC_MINTER)
    assert MINTER_ALLOWANCE == usdc.balanceOf.call(abis.USDC_MINTER)


def pull_state(evm, num_steps):
    model = UniswapModel(evm, SnapShotAgent, num_agents=1, num_steps=num_steps)
    while model.running and model.schedule.steps < num_steps:
        model.step()

    model_out = model.datacollector.get_model_vars_dataframe()
    # print(model_out.head(20))

    model_out.to_json(f"snapshot_dataframe_{num_steps}.json")

    return evm.create_snapshot()


def generate_snapshot(num_steps=10):
    # create the evm
    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    setup_usdc(evm)
    return pull_state(evm, num_steps)


def view_tick_price():
    """
    This shows the price diff is not that large between ticks.  BUT
    find the right swap to match the target is difficult and required
    a root_scalar search!
    """
    steps = 20
    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    factory_contract = abis.uniswap_factory_contract(evm)
    # get the pool address
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, abis.FEE)
    pool_contract = abis.uniswap_pool_contract(evm, pool_address)
    slot0 = pool_contract.slot0.call()
    current_price = slot0[0]
    current_tick = slot0[1]
    ticks_to_visit = [current_tick + (i + 1) * abis.TICK_SPACING for i in range(steps)]

    print(f"current sqrt_price {uniswap_math.token1_price(current_price)}")
    for i in range(steps):
        tick = ticks_to_visit[i]
        sqrt_target_price_x96 = uniswap_math.tick_to_sqrtpx96(tick)
        print(
            f"tick {tick} sqrt_price {uniswap_math.token1_price(sqrt_target_price_x96)}"
        )


if __name__ == "__main__":
    num_steps = 100
    snapshot = generate_snapshot(num_steps)
    # view_tick_price()
    with open(f"snapshot_{num_steps}.json", "w") as f:
        f.write(snapshot)
