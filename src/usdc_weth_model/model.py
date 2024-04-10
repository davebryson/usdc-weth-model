import mesa
import math

from simular import PyEvm, create_many_accounts
from usdc_weth_model import abis

from .agent import SimpleTrader


Q96 = 2**96
TICK_BASE = 1.0001
tick_space = 10

FEE = 500  # 0.5% pool
USDC_DEPOSIT = int(1e11)  # 100_000 USDC
ETH_DEPOSIT = int(1e22)  # 10_000 eth
USDC_MINTER = "0x05fbe0ad8bc8f9d3dd631d48649622add6c9ac72"


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


def x_liq(p, pb, L):
    return L * ((math.sqrt(pb) - p) / (p * math.sqrt(pb)))


def y_liq(p, pa, L):
    return L * (p - math.sqrt(pa))


## Collectors ##


def get_eth_price(model):
    slot0 = model.pool_contract.slot0.call()
    sqrtp = slot0[0]
    ep = token1_price(sqrtp)
    # print(f"eth price: {ep}")
    return ep


def get_usdc_price(model):
    slot0 = model.pool_contract.slot0.call()
    sqrtp = slot0[0]
    up = token0_price(sqrtp)
    # print(f"usdc price: {up}")
    return up


def get_x_liquidity(model):
    slot0 = model.pool_contract.slot0.call()
    P = slot0[0]
    current_tick = slot0[1]
    L = model.pool_contract.liquidity.call()

    _tb, tt = get_tick_range(current_tick, tick_space)
    pb = tick_to_price(tt)

    p_prime = P / Q96

    x = x_liq(p_prime, pb, L)
    # y = y_liq(p_prime, pa, L)

    return x / 1e6


def get_y_liquidity(model):
    slot0 = model.pool_contract.slot0.call()
    P = slot0[0]
    current_tick = slot0[1]
    L = model.pool_contract.liquidity.call()

    tb, _tt = get_tick_range(current_tick, tick_space)
    pa = tick_to_price(tb)

    p_prime = P / Q96

    y = y_liq(p_prime, pa, L)

    return y / 1e18


def active_tick(model):
    slot0 = model.pool_contract.slot0.call()
    return slot0[1]


def deposit_approve_weth(contract, agent):
    contract.deposit.transact(caller=agent, value=ETH_DEPOSIT)
    contract.approve.transact(abis.SWAP_ROUTER, ETH_DEPOSIT, caller=agent)


def transfer_and_approve_usdc(contract, agent):
    contract.transfer.transact(agent, USDC_DEPOSIT, caller=USDC_MINTER)
    contract.approve.transact(abis.SWAP_ROUTER, USDC_DEPOSIT, caller=agent)


class UniswapModel(mesa.Model):

    # args should be anything you want to pass from UI
    def __init__(self, num_agents=20, num_steps=20, swap_threshold=0.5):
        super().__init__()

        self.num_agents = num_agents
        self.num_steps = num_steps
        self.swap_threshold = swap_threshold

        self.schedule = mesa.time.RandomActivation(self)

        # load the EVM from a snapshot
        with open("./usdc-weth-snapshot.json") as f:
            snap = f.read()
        evm = PyEvm.from_snapshot(snap)

        agent_addresses = create_many_accounts(evm, num_agents, value=ETH_DEPOSIT)

        # contracts
        self.usdc_contract = abis.usdc_contract(evm)
        self.weth_contract = abis.weth_contract(evm)
        self.router_contract = abis.uniswap_router_contract(evm)
        self.factory_contract = abis.uniswap_factory_contract(evm)

        # get the pool address
        pool_address = self.factory_contract.getPool.call(abis.WETH, abis.USDC, FEE)
        self.pool_contract = abis.uniswap_pool_contract(evm, pool_address)

        # get token info
        self.token0 = self.pool_contract.token0.call()
        self.token1 = self.pool_contract.token1.call()

        # fund and approve the pool's ERC20 contracts
        for a in agent_addresses:
            deposit_approve_weth(self.weth_contract, a)
            transfer_and_approve_usdc(self.usdc_contract, a)

        # create the agents
        id = 1
        for aa in agent_addresses:
            agent = SimpleTrader(id, aa, self)
            self.schedule.add(agent)
            id += 1

        # set up data collector
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "ETH": get_eth_price,
                "USDC": get_usdc_price,
                "LIQ_ETH": get_y_liquidity,
                "LIQ_USDC": get_x_liquidity,
                "TICK": active_tick,
            }
        )

        self.running = True
        self.datacollector.collect(self)

    def step(self):
        # tell all the agents in the model to run their step function
        self.schedule.step()
        # collect data
        self.datacollector.collect(self)

    def run_model(self):
        for i in range(self.num_steps):
            self.step()
