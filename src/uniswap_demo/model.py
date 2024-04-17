import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)


import mesa
from tqdm import tqdm
from simular import create_many_accounts

from uniswap_demo import abis
from uniswap_demo.uniswap_math import *
from uniswap_demo.agent import SimpleTrader


ETH_DEPOSIT = int(1e24)
USDC_DEPOSIT = int(1e30)


## Collectors ##


def volume(model):
    v = [a.swapped_usdc for a in model.schedule.agents]
    return np.sum(v)


def get_x_liquidity(model):
    P = model.sqrtpX96
    T = model.current_tick
    L = model.liquidity

    upper_tick = get_upper_tick(T, abis.TICK_SPACING)
    pb = tick_to_price(upper_tick)
    p_prime = P / Q96
    x = x_liq(p_prime, pb, L)

    return x / 1e6


def get_y_liquidity(model):
    P = model.sqrtpX96
    T = model.current_tick
    L = model.liquidity

    lower_tick = get_lower_tick(T, abis.TICK_SPACING)
    pa = tick_to_price(lower_tick)
    p_prime = P / Q96
    y = y_liq(p_prime, pa, L)

    return y / 1e18


def deposit_approve_weth(contract, agent):
    contract.deposit.transact(caller=agent, value=ETH_DEPOSIT)
    contract.approve.transact(abis.SWAP_ROUTER, ETH_DEPOSIT, caller=agent)


def transfer_and_approve_usdc(contract, agent):
    # bal = contract.balanceOf.call(abis.USDC_MINTER)
    contract.transfer.transact(agent, USDC_DEPOSIT, caller=abis.USDC_MINTER)
    contract.approve.transact(abis.SWAP_ROUTER, USDC_DEPOSIT, caller=agent)


def get_pool_information(pool_contract):
    slot0 = pool_contract.slot0.call()
    sqrtpX96 = slot0[0]
    current_tick = slot0[1]
    l = pool_contract.liquidity.call()
    usdc_price = token0_price(sqrtpX96)
    eth_price = token1_price(sqrtpX96)
    return (sqrtpX96, current_tick, l, usdc_price, eth_price)


class UniswapModel(mesa.Model):

    def __init__(
        self, evm, agent_type, num_agents=20, num_steps=20, swap_threshold=0.5
    ):
        super().__init__()

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

        p, t, l, u, e = get_pool_information(self.pool_contract)
        self.sqrtpX96 = p
        self.current_tick = t
        self.liquidity = l
        self.usdc_price = u
        self.eth_price = e

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
                "ETH": "eth_price",
                "USDC": "usdc_price",
                "LIQ_ETH": get_y_liquidity,
                "LIQ_USDC": get_x_liquidity,
                "TICK": "current_tick",
                "VOLUME": volume,
            }
        )

        self.running = True
        self.datacollector.collect(self)

    def step(self):
        # update current pool information
        p, t, l, u, e = get_pool_information(self.pool_contract)
        self.sqrtpX96 = p
        self.current_tick = t
        self.liquidity = l
        self.usdc_price = u
        self.eth_price = e

        # tell all the agents in the model to run their step function
        self.schedule.step()

        # collect data
        self.datacollector.collect(self)

    def run_model(self):
        for i in tqdm(range(self.num_steps)):
            self.step()
