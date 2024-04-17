"""
Take a snapshot of on-chain state
"""

import os
import typing
import pandas as pd

from simular import create_account, PyEvm
from uniswap_demo import abis
from uniswap_demo.model import UniswapModel, USDC_DEPOSIT
from uniswap_demo.agent import SnapShotAgent


MINTER_ALLOWANCE = USDC_DEPOSIT


def setup_usdc(evm, num_agents=1):
    usdc = abis.usdc_contract(evm)
    master_minter = usdc.masterMinter.call()

    # Create a minter account
    create_account(evm, address=abis.USDC_MINTER)
    create_account(evm, address=master_minter)

    TOTAL_MINTER_ALLOWANCE = MINTER_ALLOWANCE * num_agents

    # grant minter status
    usdc.configureMinter.transact(
        abis.USDC_MINTER, TOTAL_MINTER_ALLOWANCE, caller=master_minter
    )
    # mint to self
    usdc.mint.transact(
        abis.USDC_MINTER, TOTAL_MINTER_ALLOWANCE, caller=abis.USDC_MINTER
    )
    assert TOTAL_MINTER_ALLOWANCE == usdc.balanceOf.call(abis.USDC_MINTER)


def pull_state(evm, num_steps) -> typing.Tuple[str, pd.DataFrame]:
    model = UniswapModel(evm, SnapShotAgent, num_agents=1, num_steps=num_steps)
    while model.running and model.schedule.steps < num_steps:
        model.step()

    # model_out = model.datacollector.get_model_vars_dataframe()
    # model_out.to_json(f"snapshot_dataframe_{num_steps}.json")

    return (evm.create_snapshot(), model.datacollector.get_model_vars_dataframe())


def generate_snapshot(num_steps=10) -> typing.Tuple[str, pd.DataFrame]:
    # create the evm
    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    setup_usdc(evm)
    return pull_state(evm, num_steps)


if __name__ == "__main__":
    num_steps = 300
    snapshot, df = generate_snapshot(num_steps)
    with open(f"./data/snapshot_{num_steps}.json", "w") as f:
        f.write(snapshot)
    df.to_json(f"./data/snapshot_dataframe_{num_steps}.json")
