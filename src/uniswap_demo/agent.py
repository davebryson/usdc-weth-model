import mesa
import random

from uniswap_demo import abis, uniswap_math
from scipy.optimize import root_scalar


class SimpleTrader(mesa.Agent):

    def __init__(self, unique_id, address, model):
        super().__init__(unique_id, model)
        self.address = address
        self.model = model

    def step(self):
        usdc_price, eth_price = self.model.current_prices
        val = random.randrange(1, 10)

        if random.random() < self.model.swap_threshold:
            # buy usdc w/eth
            amountin = (val * eth_price) * 1e18
            swapped = self.model.router_contract.exactInputSingle.transact(
                (
                    self.model.token1,
                    self.model.token0,
                    abis.FEE,
                    self.address,
                    int(1e32),
                    int(amountin),
                    0,
                    0,
                ),
                caller=self.address,
            )
            # print(f"swapped 1 ETH for {swapped/1e6} USDC")
        else:
            # buy eth w/usdc
            amountin = val * 1e6
            swapped = self.model.router_contract.exactInputSingle.transact(
                (
                    self.model.token0,
                    self.model.token1,
                    abis.FEE,
                    self.address,
                    int(1e32),
                    int(amountin),
                    0,
                    0,
                ),
                caller=self.address,
            )
            # print(f"swapped 1 USDC for {swapped/1e18} ETH")


class SnapShotAgent(mesa.Agent):
    """Need to adapt dummy agent from Verbs to do this correctly!"""

    def __init__(self, unique_id, address, model):
        super().__init__(unique_id, model)
        self.address = address
        self.model = model

        slot0 = self.model.pool_contract.slot0.call()
        current_tick = slot0[1]

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
        print("increase")
        change_sqrt_price_x96 = target - current
        change_token_1 = int(liq * change_sqrt_price_x96 / 2**96)
        if change_token_1 == 0:
            return

        def _quote_price(change_token_1):
            (_amt, p, _, _) = self.model.quoter_contract.quoteExactInputSingle.call(
                (self.model.token1, self.model.token0, int(change_token_1), abis.FEE, 0)
            )

            # quoted_price = q[1]
            # print(f"increases quoted: {quoted_price}")
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

    def swap_to_decrease(self, target, current, liq, current_eth_price):
        print("decrease")
        change_sqrt_price_x96 = current - target
        change_token_1 = int(liq * change_sqrt_price_x96 / 2**96)
        if change_token_1 == 0:
            return

        print(f"looking for: {change_token_1}")

        def _quote_price(change_token_1):
            (_amt, p, _, _) = self.model.quoter_contract.quoteExactOutputSingle.call(
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

        print(f"quoted: {change_token_1}")
        # adjust price for USDC decimals??
        # amount_in = change_token_1 / current_eth_price / 1e12
        # print(f"adj: {amount_in}")

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

        print(f"{self.model.schedule.steps}...")

        sqrt_target_price_x96 = uniswap_math.tick_to_sqrtpx96(
            self.ticks_to_visit[self.model.schedule.steps]
        )

        (sqrt_current_price_x96, liquidity) = self.get_current_sqrtp_and_liquidity()
        current_eth_price = uniswap_math.token1_price(sqrt_current_price_x96)

        if sqrt_target_price_x96 > sqrt_current_price_x96:
            # buy usdc w/eth
            # Note amount here is in eth which is ok
            got = self.swap_to_increase(
                sqrt_target_price_x96, sqrt_current_price_x96, liquidity
            )
            if got:
                print(f"bought {got/1e6} USDC")
        else:
            # buy eth w/usdc (1e6)
            # here we need to convert amount_in (in eth) to
            # the appropriate conversion rate to USDC.
            got = self.swap_to_decrease(
                sqrt_target_price_x96,
                sqrt_current_price_x96,
                liquidity,
                current_eth_price,
            )
            if got:
                print(f"bought {got/1e18} ETH")
