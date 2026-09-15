# Munder Difflin Multi-Agent System

A text-based multi-agent workflow for paper inventory, quoting, purchase evaluation and fulfillment, and financial reporting. The implementation uses Pydantic AI, Pydantic models, SQLAlchemy, and SQLite.

## Project files

- `project_starter.py` — backward-compatible entry point and exports for the original starter API.
- `munder_difflin/` — modular application package:
  - `database_setup.py` creates and seeds the exercise database; `database.py` contains database access and transaction helpers.
  - `schemas.py` defines shared Pydantic input and result models; `catalog.py` holds catalog and pricing constants.
  - `tools/` contains inventory, quoting, and sales tools.
  - `agents/` contains one factory module per agent and the shared `AgentSystem` builder.
  - `catalog_matching.py` validates semantic product matches; `dispatch.py` routes requests.
  - `evaluation.py` runs the supplied scenarios; `cli.py` configures the runtime and starts the evaluation.
- `quote_requests_sample.csv` — evaluation scenarios.
- `quotes.csv` and `quote_requests.csv` — historical quote data.
- `diagrams/` — architecture and order-lifecycle diagrams.
- `design_notes.md` — system design, evaluation, limitations, and improvement proposals.

## Setup and execution

Install dependencies with `uv sync` (or `pip install -r requirements.txt`). Configure the Vocareum-compatible API credentials and model settings in `.env` using `UDACITY_OPENAI_API_KEY` and `UDACITY_MODEL_NAME`. Run the script from this directory:

```bash
python project_starter.py
```

The package entry point is also available as `uv run python -m munder_difflin`.

The evaluation calls the model, initializes the SQLite database, simulates the dated scenarios, and writes `test_results.csv`. Keep the generated CSV and console output together as evidence from the same run.

## Architecture and evaluation

The system uses at most five agents: an orchestrator plus Inventory, Quotes, Sales, and Reporting specialists. The orchestrator extracts a structured request, resolves all requested lines against the catalog, and routes the validated request. Sales reserves inventory and replenishment funds for feasible pending orders; scheduled processing records receipts and completes orders as dates advance.

See [`design_notes.md`](design_notes.md) for detailed responsibilities, pricing and fulfillment rules, evaluation status, known limitations, and proposed improvements.
