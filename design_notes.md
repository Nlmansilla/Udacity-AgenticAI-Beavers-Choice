# Munder Difflin Multi-Agent System — Design and Evaluation

## System overview

This project implements a text-based workflow for inventory questions, quote requests, purchases, and financial reports. It uses Pydantic AI with an OpenAI-compatible Vocareum endpoint, Pydantic models for structured inputs and outputs, and SQLite for transactions, orders, and replenishment reservations.

The system has five agents total: one orchestrator and four specialist workers. The orchestrator extracts intent, products, quantities, units, and deadlines into a `ParsedCustomerRequest`. It then runs a catalog-matching pass using the same agent with temporary instructions and structured `CatalogMatch` output. Python validates match coverage and product names, checks catalog sales units, and routes the normalized request through `dispatch_request`.

This architecture keeps the language model on tasks that need language understanding, such as intent extraction and semantic catalog matching. Deterministic Python checks enforce complete item coverage, catalog names, units, pricing, inventory, deadlines, and funding before database writes. The explicit Python dispatcher keeps routing and authorization rules visible, while each worker owns one business area. The design stays within the five-agent limit and avoids letting the orchestrator perform transactions directly.

The specialist agents are:

- **Inventory Agent:** evaluates a requested product and lists available inventory. Available stock accounts for active reservations. Supplier dates are estimates based on `get_supplier_delivery_date`.
- **Quotes Agent:** searches historical quote data and calculates a deterministic quote. The implementation treats catalog `unit_price` as acquisition cost, adds a 25% markup, and applies a 5% discount at 500 units or a 10% discount at 1,000 units per product.
- **Sales Agent:** evaluates deadlines, inventory, reservations, and cash before calling `fulfill_order`. The tool records direct sales atomically, supports order IDs for idempotent retries, or creates a pending order with stock and cash reservations when replenishment is required.
- **Reporting Agent:** answers cash, inventory, and financial-report questions using the starter helper functions.

## Code organization

The implementation is split into the `munder_difflin` package by responsibility. `database_setup.py` creates and seeds the exercise schema, while `database.py` owns database queries and transaction helpers. Shared Pydantic contracts live in `schemas.py`; inventory, quote, and sales tools live in separate modules under `tools/`. Each agent has a factory in `agents/`, and `agents.build_agent_system` creates the five agents around one model configuration. Catalog resolution and request routing are in `catalog_matching.py` and `dispatch.py`; the scenario runner is isolated in `evaluation.py`. `project_starter.py` remains a small compatibility entry point for the original assignment interface. The setup script recreates the exercise tables and seed data on each evaluation run; a versioned migration framework is unnecessary for this fixed, local exercise schema.

`process_pending_orders(as_of_date)` runs from the scenario harness before each customer request. It records due supplier receipts, then records the sale and releases reservations when all lines are available. Replenishment receipts, sales, reservation updates, and order-result changes use a database transaction.

The architecture diagram is [`diagrams/diagram.png`](diagrams/diagram.png), with editable sources in [`diagrams/diagram.drawio`](diagrams/diagram.drawio) and [`diagrams/diagram.svg`](diagrams/diagram.svg). [`diagrams/workflow.png`](diagrams/workflow.png) is the earlier workflow sketch.

## Data and business rules

- `paper_supplies` is the catalog source. Each product has a canonical name, category, acquisition `unit_price`, and sales unit. Some specialty products have an unspecified unit and must not be quoted or sold until clarified.
- Duplicate product lines are consolidated before stock assessment and quoting.
- Bulk discounts apply to each product's consolidated quantity.
- A purchase is rejected when the delivery deadline is infeasible or the replenishment cost exceeds unreserved cash.
- If replenishment is feasible, the system reserves existing stock and the funds needed for the shortage. It records neither a purchase nor a sale until the supplier's estimated arrival date.
- `fulfilled` means that the sale transaction was recorded in the simulation. It does not mean the goods were physically shipped or delivered to the customer.
- Unsupported items and ambiguous specifications must be retained in the structured request and must block execution until resolved. No partial order should silently drop a line.

## Evaluation

The evaluation uses the 20 requests in `quote_requests_sample.csv` and appends three standalone quote cases. The current `test_results.csv` contains all 23 results from one run. The three quote cases exercise ordinary catalog items at quantities below, at, and above the bulk-discount thresholds:

| Quote case | Requested item | Result | Discount |
|---|---|---:|---:|
| `quote-1` | 100 sheets of A4 paper | $6.25 | 0% |
| `quote-2` | 600 sheets of Cardstock | $106.88 | 5% |
| `quote-3` | 1,200 sheets of Letter-sized paper | $81.00 | 10% |

All three were parsed as quote requests, matched to the expected catalog products, and recorded with `final_status=quoted`. Their deterministic `quote_assessment` values match the customer-facing breakdowns. Each has a zero `final_sale_amount`, and the cash and inventory balances are unchanged across the quote rows, confirming that quoting did not record a transaction.

Of the 20 purchase scenarios, four ended with `final_status=fulfilled` and 16 with `final_status=no_order_record`; every no-order result includes a reason. The evaluation therefore did not fulfill every purchase request, and the CSV records the reasons. The cash balance changes across four transitions in the purchase results, exceeding the rubric's minimum of three requests that change the balance. No purchase request remained pending at the end of this run. The CSV is the current evaluation evidence; a console log from the same run is not present in the workspace.

Known limitations include the LLM's semantic catalog-matching judgment, intentionally conservative handling of color/size/material claims not represented in the catalog, and supplier delivery being an estimate rather than a confirmed external order. The successful quote tests cover three canonical products, not every wording or product combination. The model should not be allowed to weaken the deterministic checks for match coverage, canonical catalog names, units, cash, deadlines, or database writes.

## Strengths

- Structured Pydantic requests keep intent, quantities, units, dates, and order IDs explicit.
- Pricing, stock, delivery, and cash calculations are implemented in deterministic tools rather than delegated to free-form model arithmetic.
- In the recorded run, all three standalone quote cases returned the expected catalog item and total, including the 0%, 5%, and 10% discount tiers; quote rows recorded no sale and did not change cash or inventory.
- The purchase evaluation recorded four sales and left 16 requests without an order, with a reason for each. This shows that the system can complete eligible requests while explaining why others were not recorded.
- Pending orders reserve resources, process supplier receipts by simulated date, and can be retried by stable order ID.
- Transactional writes prevent a partially recorded multi-line sale when a database operation fails.
- The design stays within the five-agent limit and includes the required inventory, cash, and financial-report helpers.

## Further improvements

1. **Improve catalog data and matching tests.** Add reviewed aliases and supported attributes to the canonical catalog, then test every scenario's original line against its proposed match. Keep ambiguous product properties and unsupported goods as clarification or rejection results.
2. **Strengthen concurrent reservation safety.** The current assessment-then-write sequence is safe for the sequential simulator but can race if simultaneous requests inspect the same stock or cash. Perform availability checks and reservation writes under a serialized database transaction, and add a concurrent-request test.
3. **Preserve complete evaluation evidence.** Keep the console log with the CSV from the same run and record the run date or code revision, so model outputs and status counts can be reproduced and traced.
4. **Persist accepted pricing.** Store the accepted quote with each pending order so later catalog or discount-policy changes cannot alter the sale amount at fulfillment.

## Running and submitting

Set `UDACITY_OPENAI_API_KEY` and the configured model name for the Vocareum-compatible endpoint, install the dependencies from `requirements.txt`, and run `project_starter.py` from the project directory. The scenario evaluation makes model calls and writes `test_results.csv`; retain that file and the console output from the same run for final evaluation evidence.
