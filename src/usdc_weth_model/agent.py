"""
Hello
"""

import mesa
import random

FEE = 500  # 0.5% pool


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
                    FEE,
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
                    FEE,
                    self.address,
                    int(1e32),
                    int(amountin),
                    0,
                    0,
                ),
                caller=self.address,
            )
            # print(f"swapped 1 USDC for {swapped/1e18} ETH")
