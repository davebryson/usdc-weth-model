import os
import os.path
import random
import math

from simular import PyEvm, create_account, create_many_accounts

from usdc_weth_model import abis

FEE = 500  # 0.5% pool
USDC_DEPOSIT = int(1e11)  # 100_000 USDC
ETH_DEPOSIT = int(1e22)  # 10_000 eth

USDC_DECIMALS = 1e6
WETH_DECIMALS = 1e18

USDC_MINTER = "0x05fbe0ad8bc8f9d3dd631d48649622add6c9ac72"
MINTER_ALLOWANCE = int(1e8 * USDC_DECIMALS)  # 100_000_000 USDC

Q96 = 2**96


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


def setup_usdc(evm):
    usdc = abis.usdc_contract(evm)
    master_minter = usdc.masterMinter.call()

    # Create a minter account
    create_account(evm, address=USDC_MINTER)
    create_account(evm, address=master_minter)

    # grant minter status
    usdc.configureMinter.transact(USDC_MINTER, MINTER_ALLOWANCE, caller=master_minter)
    # mint to self
    usdc.mint.transact(USDC_MINTER, MINTER_ALLOWANCE, caller=USDC_MINTER)

    assert MINTER_ALLOWANCE == usdc.balanceOf.call(USDC_MINTER)


def generate_snapshsot(evm):

    # contracts
    usdc_contract = abis.usdc_contract(evm)
    weth_contract = abis.weth_contract(evm)
    router_contract = abis.uniswap_router_contract(evm)
    factory_contract = abis.uniswap_factory_contract(evm)

    # get the pool address
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, FEE)
    pool_contract = abis.uniswap_pool_contract(evm, pool_address)

    dummy_agent = create_account(evm, value=ETH_DEPOSIT)

    # get token info
    token0 = pool_contract.token0.call()
    token1 = pool_contract.token1.call()
    pool_contract.slot0.call()

    # deposit and approve weth
    deposit_approve_weth(weth_contract, dummy_agent)

    # mint and approve usdc
    transfer_and_approve_usdc(usdc_contract, dummy_agent)

    # verify balances and allowances
    assert ETH_DEPOSIT == weth_contract.balanceOf.call(dummy_agent)
    assert USDC_DEPOSIT == usdc_contract.balanceOf.call(dummy_agent)

    assert ETH_DEPOSIT == weth_contract.allowance.call(dummy_agent, abis.SWAP_ROUTER)
    assert USDC_DEPOSIT == usdc_contract.allowance.call(dummy_agent, abis.SWAP_ROUTER)

    swapped = router_contract.exactInputSingle.transact(
        (
            token1,
            token0,
            FEE,
            dummy_agent,
            int(1e32),
            int(1e18),
            0,
            0,
        ),
        caller=dummy_agent,
    )

    print(f"got: {swapped/1e6}")

    return evm.create_snapshot()


def build_snapshot():
    evm = PyEvm.from_fork(url=os.environ["ALCHEMY"])
    setup_usdc(evm)
    snapshot = generate_snapshsot(evm)
    with open("usdc-weth-snapshot.json", "w") as f:
        f.write(snapshot)
    print("done")


def deposit_approve_weth(contract, agent):
    contract.deposit.transact(caller=agent, value=ETH_DEPOSIT)
    contract.approve.transact(abis.SWAP_ROUTER, ETH_DEPOSIT, caller=agent)


def transfer_and_approve_usdc(contract, agent):
    contract.transfer.transact(agent, USDC_DEPOSIT, caller=USDC_MINTER)
    contract.approve.transact(abis.SWAP_ROUTER, USDC_DEPOSIT, caller=agent)


def run_agents(evm, num_agents):
    agents = create_many_accounts(evm, num_agents, value=ETH_DEPOSIT)

    # contracts
    usdc_contract = abis.usdc_contract(evm)
    weth_contract = abis.weth_contract(evm)
    router_contract = abis.uniswap_router_contract(evm)
    factory_contract = abis.uniswap_factory_contract(evm)

    # get the pool address
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, FEE)
    pool_contract = abis.uniswap_pool_contract(evm, pool_address)

    # get token info
    token0 = pool_contract.token0.call()
    token1 = pool_contract.token1.call()
    slot0b = pool_contract.slot0.call()
    print(f"{slot0b}")

    for a in agents:
        deposit_approve_weth(weth_contract, a)
        transfer_and_approve_usdc(usdc_contract, a)

    for a in agents:
        # try some trades!
        swapped = router_contract.exactInputSingle.transact(
            (
                token1,
                token0,
                FEE,
                a,
                int(1e32),
                int(1e18),
                0,
                0,
            ),
            caller=a,
        )
        print(f"got: {swapped/1e6}")

    slot0a = pool_contract.slot0.call()
    print(f"{slot0a}")

    print("done")


## start Agent Behavior


def uniswap_trader(agent, token0, token1, usdc, weth, pool, router, threshold=0.5):

    slot0 = pool.slot0.call()
    sqrtp = slot0[0]
    tick = slot0[1]
    usdc_price = token0_price(sqrtp)
    weth_price = token1_price(sqrtp)

    # print(f"tick: {tick}")
    print(f"usdc: {usdc_price}")
    # print(f"weth: {weth_price}")

    # calculate liquidity here

    # NOTE: amountins are based on the exchange rate
    # which in this case is token1/token0 (weth/usdc).

    if random.random() < threshold:
        # print("buy")
        # exchange 1 ether for USDC
        amountin = int(1e18)  # buy 1 eth worth of USDC
        swapped = router.exactInputSingle.transact(
            (
                token1,
                token0,
                FEE,
                agent,
                int(1e32),
                amountin,
                0,
                0,
            ),
            caller=agent,
        )
        print(f"bought: {swapped/1e6} USDC for {amountin} ETHER")
    else:
        print("----------")
        print("sell")
        # exchange USDC for 1 Ether
        # bal = usdc.balanceOf.call("0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640")
        # print(f"bal of USDC: {bal}")
        print(f"cost per ether: {usdc_price}")

        amountin = int(usdc_price * 1e6)

        # if bal < amountin:
        #    amountin = bal

        # print(f"amountin: {amountin}")
        # try to buy 1 ether with USDC should = usdc_price * 1e6
        ubal = usdc.balanceOf.call(agent)
        wbal = weth.balanceOf.call(agent)
        print(f"agent balance")
        print(f"usdc: {ubal}")
        print(f"weth: {wbal}")
        swapped = router.exactInputSingle.transact(
            (
                token0,
                token1,
                FEE,
                agent,
                int(1e32),
                amountin,
                0,
                0,
            ),
            caller=agent,
        )

        print(f"sold {amountin} usdc for : {swapped/1e18} WETH")
        print("----------")


def agent_model(evm, num_agents, n_steps):
    agents = create_many_accounts(evm, num_agents, value=ETH_DEPOSIT)
    # contracts
    usdc_contract = abis.usdc_contract(evm)
    weth_contract = abis.weth_contract(evm)
    router_contract = abis.uniswap_router_contract(evm)
    factory_contract = abis.uniswap_factory_contract(evm)

    # get the pool address
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, FEE)
    pool_contract = abis.uniswap_pool_contract(evm, pool_address)

    # get token info
    token0 = pool_contract.token0.call()
    token1 = pool_contract.token1.call()
    # slot0b = pool_contract.slot0.call()
    # print(f"{slot0b}")

    for a in agents:
        deposit_approve_weth(weth_contract, a)
        transfer_and_approve_usdc(usdc_contract, a)

    # sim
    for i in range(n_steps):
        slot0b = pool_contract.slot0.call()
        print("***************************")
        print(f"current tick: {slot0b[1]}")
        print("***************************")
        for a in agents:
            uniswap_trader(
                a,
                token0,
                token1,
                usdc_contract,
                weth_contract,
                pool_contract,
                router_contract,
                threshold=0.5,
            )


### LIQ STUFF ###


def liquidity0(amount, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    return (amount * (pa * pb) / Q96) / (pb - pa)


def liquidity1(amount, pa, pb):
    if pa > pb:
        pa, pb = pb, pa
    return amount * Q96 / (pb - pa)


def calc_liquidity(evm):

    usdc_contract = abis.usdc_contract(evm)
    weth_contract = abis.weth_contract(evm)

    usdc_total = usdc_contract.totalSupply.call()
    weth_total = weth_contract.totalSupply.call()

    print("totals")
    print(f"usdc: {usdc_total}")
    print(f"weth: {weth_total}")

    eth = 10**18

    price_low = 3600
    price_cur = 3697
    price_upp = 3700

    sqrtp_low = price_to_sqrtp(price_low)
    sqrtp_cur = price_to_sqrtp(price_cur)
    sqrtp_upp = price_to_sqrtp(price_upp)

    amount_eth = 1 * eth
    amount_usdc = 3697 * eth

    liq0 = liquidity0(amount_eth, sqrtp_cur, sqrtp_upp)
    print(f"liq0: {liq0}")
    liq1 = liquidity1(amount_usdc, sqrtp_cur, sqrtp_low)
    print(f"liq1: {liq1}")
    liq = int(min(liq0, liq1))

    print(f"Deposit: {amount_eth/eth} ETH, {amount_usdc/eth} USDC; liquidity: {liq}")


def get_pool_values(evm):
    factory_contract = abis.uniswap_factory_contract(evm)
    pool_address = factory_contract.getPool.call(abis.WETH, abis.USDC, FEE)
    pool = abis.uniswap_pool_contract(evm, pool_address)
    slot0 = pool.slot0.call()
    print(slot0)
    sqrtp = slot0[0]

    current_tick = slot0[1]
    L = pool.liquidity.call()

    print(f"sqrtp: {sqrtp}")
    print(f"current tick: {current_tick}")
    print(f"liq: {L}")


if __name__ == "__main__":
    with open("./usdc-weth-snapshot.json") as f:
        snap = f.read()
    evm = PyEvm.from_snapshot(snap)
    agent_model(evm, 3, 50)

    # get_pool_values(evm)
