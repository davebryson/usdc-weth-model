import mesa

from .model import UniswapModel


# Green
USDC_COLOR = "#00A36C"
# Red
ETH_COLOR = "#0096FF"

model_params = {
    "num_agents": mesa.visualization.Slider(
        "Traders",
        min_value=3,
        max_value=50,
        value=20,
        step=1,
        description="Number of Trader Agents",
    ),
    "swap_threshold": mesa.visualization.Slider(
        "SwapThreshold",
        min_value=0.2,
        max_value=0.9,
        value=0.5,
        step=0.1,
        description="When to buy vs sell",
    ),
}


eth_chart_element = mesa.visualization.ChartModule(
    [
        {"Label": "ETH", "Color": ETH_COLOR},
    ]
)

usdc_chart_element = mesa.visualization.ChartModule(
    [
        {"Label": "USDC", "Color": USDC_COLOR},
    ]
)

u_liquidity_element = mesa.visualization.ChartModule(
    [
        {"Label": "LIQ_USDC", "Color": USDC_COLOR},
    ]
)

e_liquidity_element = mesa.visualization.ChartModule(
    [
        {"Label": "LIQ_ETH", "Color": ETH_COLOR},
    ]
)

tick_element = mesa.visualization.ChartModule(
    [
        {"Label": "TICK", "Color": ETH_COLOR},
    ]
)

# create instance of Mesa ModularServer
server = mesa.visualization.ModularServer(
    UniswapModel,
    [
        tick_element,
        e_liquidity_element,
        u_liquidity_element,
        eth_chart_element,
        usdc_chart_element,
    ],
    "USDC Model",
    model_params=model_params,
)
