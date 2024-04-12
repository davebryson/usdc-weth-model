from simular import PyAbi, Contract
from pathlib import Path

PATH = Path(__file__).parent


# AGENT = "0xcfda354f04e741f2c902b86da7292ce9ef517039"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
SWAP_ROUTER = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
USDC_MINTER = "0x05fbe0ad8bc8f9d3dd631d48649622add6c9ac72"
UNISWAP_FACTORY = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
UNISWAP_QUOTER = "0x61fFE014bA17989E743c5F6cB21bF9697530B21e"


# WETH/USDC Pool.  We get it dynamically in the script. Added here
# just for reference: 0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640

FEE = 500  # 0.5% pool
TICK_SPACING = 10


def uniswap_factory_contract(evm):
    with open(f"{PATH}/UniswapV3Factory.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(UNISWAP_FACTORY)


def uniswap_router_contract(evm):
    with open(f"{PATH}/SwapRouter.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(SWAP_ROUTER)


def uniswap_pool_contract(evm, pool_address):
    with open(f"{PATH}/UniswapV3Pool.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(pool_address)


def uniswap_quoter_contract(evm):
    with open(f"{PATH}/Quoter_v2.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(UNISWAP_QUOTER)


def weth_contract(evm):
    with open(f"{PATH}/weth.abi") as f:
        abi = f.read()
    abi = PyAbi.from_abi_bytecode(abi, None)
    return Contract(evm, abi).at(WETH)


def usdc_contract(evm):
    abi0 = [
        "function totalSupply() (uint256)",
        "function balanceOf(address) (uint256)",
        "function masterMinter() (address)",
        "function configureMinter(address, uint256) (bool)",
        "function mint(address, uint256) (bool)",
        "function burn(uint256)",
        "function minterAllowance(address) (uint256)",
        "function approve(address, uint256) (bool)",
        "function transfer(address, uint256) (bool)",
        "function allowance(address, address) (uint256)",
    ]
    abi = PyAbi.from_human_readable(abi0)
    return Contract(evm, abi).at(USDC)
