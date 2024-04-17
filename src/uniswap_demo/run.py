from simular import PyEvm
from uniswap_demo.model import UniswapModel
from uniswap_demo.agent import SimpleTrader
from uniswap_demo.snapshot import setup_usdc


if __name__ == "__main__":
    num_steps = 500
    num_agents = 20
    with open("./data/snapshot_300.json") as f:
        snapshot = f.read()

    evm = PyEvm.from_snapshot(snapshot)

    # need to make sure USDC is allocated to agents
    setup_usdc(evm, num_agents)

    model = UniswapModel(evm, SimpleTrader, num_agents=num_agents, num_steps=num_steps)
    model.run_model()
