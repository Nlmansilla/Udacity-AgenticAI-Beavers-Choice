# Munder Difflin Multi-Agent System

A text-based multi-agent workflow for paper inventory, quoting, purchase evaluation and fulfillment, and financial reporting. The implementation uses Pydantic AI, Pydantic models, SQLAlchemy, and SQLite.

## Project files

- `project_starter.py` — agents, tools, database helpers, and scenario runner.
- `quote_requests_sample.csv` — evaluation scenarios.
- `quotes.csv` and `quote_requests.csv` — historical quote data.
- `diagrams/` — architecture and order-lifecycle diagrams.
- `design_notes.md` — system design, evaluation, limitations, and improvement proposals.

## Setup and execution

Install dependencies with `pip install -r requirements.txt`. Configure the Vocareum-compatible API credentials and model settings in `.env` using the variable names expected by `project_starter.py`. Run the script from this directory:

```bash
python project_starter.py
```

The evaluation calls the model, initializes the SQLite database, simulates the dated scenarios, and writes `test_results.csv`. Keep the generated CSV and console output together as evidence from the same run.

## Architecture and evaluation

The system uses at most five agents: an orchestrator plus Inventory, Quotes, Sales, and Reporting specialists. The orchestrator extracts a structured request, resolves all requested lines against the catalog, and routes the validated request. Sales reserves inventory and replenishment funds for feasible pending orders; scheduled processing records receipts and completes orders as dates advance.

See [`design_notes.md`](design_notes.md) for detailed responsibilities, pricing and fulfillment rules, evaluation status, known limitations, and proposed improvements.
