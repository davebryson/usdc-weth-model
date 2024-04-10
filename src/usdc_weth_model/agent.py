import mesa
import random

FEE = 500  # 0.5% pool


class SimpleTrader(mesa.Agent):

    def __init__(self, unique_id, address, model):
        super().__init__(unique_id, model)
        self.address = address
        self.model = model

        # print(
        #    f" agent: {unique_id}  address: {self.address}  token0: {self.model.token0}"
        # )

    def step(self):
        if random.random() < self.model.swap_threshold:
            swapped = self.model.router_contract.exactInputSingle.transact(
                (
                    self.model.token1,
                    self.model.token0,
                    FEE,
                    self.address,
                    int(1e32),
                    int(1e18),
                    0,
                    0,
                ),
                caller=self.address,
            )
            # print(f"swapped 1 ETH for {swapped/1e6} USDC")
        else:
            swapped = self.model.router_contract.exactInputSingle.transact(
                (
                    self.model.token0,
                    self.model.token1,
                    FEE,
                    self.address,
                    int(1e32),
                    int(3500 * 1e6),
                    0,
                    0,
                ),
                caller=self.address,
            )
            # print(f"swapped 1 USDC for {swapped/1e18} ETH")