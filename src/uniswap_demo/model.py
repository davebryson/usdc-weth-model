import mesa
from simular import PyEvm, create_many_accounts

from uniswap_demo import abis
from uniswap_demo.uniswap_math import *
from uniswap_demo.agent import SimpleTrader


ETH_DEPOSIT = int(1e24)
USDC_DEPOSIT = int(1e30)


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

    _tb, tt = get_tick_range(current_tick, abis.TICK_SPACING)
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

    tb, _tt = get_tick_range(current_tick, abis.TICK_SPACING)
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
    bal = contract.balanceOf.call(abis.USDC_MINTER)
    print(f"BALANCE: {bal}")
    contract.transfer.transact(agent, USDC_DEPOSIT, caller=abis.USDC_MINTER)
    contract.approve.transact(abis.SWAP_ROUTER, USDC_DEPOSIT, caller=agent)


class UniswapModel(mesa.Model):

    def __init__(
        self, evm, agent_type, num_agents=20, num_steps=20, swap_threshold=0.5
    ):
        super().__init__()

        self.current_prices = (0, 0)
        self.num_agents = num_agents
        self.num_steps = num_steps
        self.swap_threshold = swap_threshold
        self.schedule = mesa.time.RandomActivation(self)

        # contracts
        self.usdc_contract = abis.usdc_contract(evm)
        self.weth_contract = abis.weth_contract(evm)
        self.router_contract = abis.uniswap_router_contract(evm)
        self.factory_contract = abis.uniswap_factory_contract(evm)
        self.quoter_contract = abis.uniswap_quoter_contract(evm)

        # get the pool address
        pool_address = self.factory_contract.getPool.call(
            abis.WETH, abis.USDC, abis.FEE
        )
        self.pool_contract = abis.uniswap_pool_contract(evm, pool_address)

        agent_addresses = create_many_accounts(evm, num_agents, value=ETH_DEPOSIT)

        # get token info
        self.token0 = self.pool_contract.token0.call()
        self.token1 = self.pool_contract.token1.call()

        # fund and approve the pool's ERC20 contracts and create the agent
        id = 1
        for a in agent_addresses:
            deposit_approve_weth(self.weth_contract, a)
            transfer_and_approve_usdc(self.usdc_contract, a)

            agent = agent_type(id, a, self)
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

    def __update_current_prices(self):
        slot0 = self.pool_contract.slot0.call()
        sqrtp = slot0[0]
        usdc = token0_price(sqrtp)
        eth = token1_price(sqrtp)
        self.current_prices = (usdc, eth)

    def step(self):
        self.__update_current_prices()

        # tell all the agents in the model to run their step function
        self.schedule.step()

        # collect data
        self.datacollector.collect(self)

    def run_model(self):
        for i in range(self.num_steps):
            self.step()
