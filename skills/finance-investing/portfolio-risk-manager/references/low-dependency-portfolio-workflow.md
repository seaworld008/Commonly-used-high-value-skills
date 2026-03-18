# Low Dependency Portfolio Workflow

If the environment is plain Python and you want to avoid scientific dependencies:

1. use `scripts/portfolio_risk.py` for descriptive risk views
2. use `scripts/build_optimizer_inputs.py` to generate expected returns and a covariance matrix
3. pass the output into a heavier optimizer only when needed

This keeps the first-pass workflow portable across AI coding tools and lightweight local environments.

