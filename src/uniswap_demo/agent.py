import mesa
import random

from uniswap_demo import abis, uniswap_math
from scipy.optimize import root_scalar


class SimpleTrader(mesa.Agent):

    def __init__(self, unique_id, address, model):
        super().__init__(unique_id, model)
        self.address = address
        self.model = model
        self.swapped_usdc = 0.0

    def step(self):
        """Swapping USDC and WETH"""
        if random.random() < self.model.swap_threshold:
            # buy 1 eth worth of usdc
            swapped = self.model.router_contract.exactInputSingle.transact(
                (
                    self.model.token1,
                    self.model.token0,
                    abis.FEE,
                    self.address,
                    int(1e32),
                    int(1e18),  # amount in
                    0,
                    0,
                ),
                caller=self.address,
            )
            self.swapped_usdc += swapped / 1e6
            # print(f"bought: {swapped/1e6} USDC")
        else:
            # sell usdc to get 1 eth.
            swapped = self.model.router_contract.exactOutputSingle.transact(
                (
                    self.model.token0,
                    self.model.token1,
                    abis.FEE,
                    self.address,
                    int(1e32),
                    int(1e18),
                    int(1e32),
                    0,
                ),
                caller=self.address,
            )

            self.swapped_usdc -= swapped / 1e6
            # print(f"Sold: {swapped/1e6} USDC")


class SnapShotAgent(mesa.Agent):
    """
    Agent used solely to populate contract storage slots for modeling a trader
    """

    def __init__(self, unique_id, address, model):
        super().__init__(unique_id, model)
        self.address = address
        self.model = model

        # track agent's swap balances:
        self.swapped_usdc = 0.0

        current_tick = self.model.current_tick

        self.ticks_to_visit = [
            current_tick + (i + 1) * abis.TICK_SPACING
            for i in range(self.model.num_steps // 2)
        ]
        self.ticks_to_visit.extend(
            [
                current_tick + (i + 1) * abis.TICK_SPACING
                for i in range(self.model.num_steps // 2)
            ]
        )

    def swap_to_increase(self, target, current, liq):
        change_sqrt_price_x96 = target - current
        change_token_1 = int(liq * change_sqrt_price_x96 / 2**96)
        if change_token_1 == 0:
            return

        def _quote_price(change_token_1):
            (_, p, _, _) = self.model.quoter_contract.quoteExactInputSingle.call(
                (self.model.token1, self.model.token0, int(change_token_1), abis.FEE, 0)
            )
            return p

        try:
            sol = root_scalar(
                lambda x: _quote_price(x) - target,
                x0=change_token_1 // 2,  # initial guess
                method="newton",
                maxiter=5,
            )
            change_token_1 = sol.root
        except:
            return None

        swap = self.model.router_contract.exactInputSingle.transact(
            (
                self.model.token1,
                self.model.token0,
                abis.FEE,
                self.address,
                int(1e32),
                int(change_token_1),
                0,
                0,
            ),
            caller=self.address,
        )

        return swap

    def swap_to_decrease(self, target, current, liq):
        change_sqrt_price_x96 = current - target
        change_token_1 = int(liq * change_sqrt_price_x96 / 2**96)
        if change_token_1 == 0:
            return

        def _quote_price(change_token_1):
            (_, p, _, _) = self.model.quoter_contract.quoteExactOutputSingle.call(
                (self.model.token0, self.model.token1, int(change_token_1), abis.FEE, 0)
            )
            return p

        try:
            sol = root_scalar(
                lambda x: _quote_price(x) - target,
                x0=change_token_1 // 2,
                method="newton",
                maxiter=5,
            )
            change_token_1 = sol.root
        except:
            return None

        swap = self.model.router_contract.exactOutputSingle.transact(
            (
                self.model.token0,
                self.model.token1,
                abis.FEE,
                self.address,
                int(1e32),
                int(change_token_1),
                int(1e32),
                0,
            ),
            caller=self.address,
        )

        return swap

    def get_current_sqrtp_and_liquidity(self):
        slot0 = self.model.pool_contract.slot0.call()
        liquidity = self.model.pool_contract.liquidity.call()
        current_price = slot0[0]
        return (current_price, liquidity)

    def step(self):
        sqrt_target_price_x96 = uniswap_math.tick_to_sqrtpx96(
            self.ticks_to_visit[self.model.schedule.steps]
        )

        sqrt_current_price_x96 = self.model.sqrtpX96
        liquidity = self.model.liquidity

        # current_eth_price = uniswap_math.token1_price(sqrt_current_price_x96)

        if sqrt_target_price_x96 > sqrt_current_price_x96:
            got = self.swap_to_increase(
                sqrt_target_price_x96, sqrt_current_price_x96, liquidity
            )
            if got:
                self.swapped_usdc += got / 1e6
        else:
            got = self.swap_to_decrease(
                sqrt_target_price_x96, sqrt_current_price_x96, liquidity
            )
            if got:
                self.swapped_usdc -= got / 1e6
