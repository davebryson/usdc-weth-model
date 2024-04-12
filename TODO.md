
- Refactor code
- Check math on balances, etc...
- use the notebook approach for demo

Note that we've probably only cached the pool for a given tick interval.
We have to keep trades moderate to not go outside that interval and cause STF (lack of pool funds?) errors.

*** How can I fork more liquidity for other ticks? This is exactly what the dummyagent does to 
pull liquidty for the range of steps from ticks.  He has the agent swap in those ranges to pull
state.

Note: you'll need to build snapshots based on the number of model steps

** Finding the quoted exact price using root_scalar is REQUIRED. Other wise price diffs 
are so large the search over many steps drains the agents balance!  Forking the initial 
snapshot is a heavier lift than the simulation!

- What am I showing??
- How can I better explain the charts?

See the swap chart in the V3 dev book : https://uniswapv3book.com/milestone_1/introduction.html

Note how in the graphs, things are the inverse of each other ... ETH vs USDC on trades

