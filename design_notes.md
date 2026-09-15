# Munder Difflin Multi-Agent System — Design and Evaluation

## System overview

This project implements a text-based workflow for inventory questions, quote requests, purchases, and financial reports. It uses Pydantic AI with an OpenAI-compatible Vocareum endpoint, Pydantic models for structured inputs and outputs, and SQLite for transactions, orders, and replenishment reservations.

The system has five agents total: one orchestrator and four specialist workers. The orchestrator extracts intent, products, quantities, units, and deadlines into a `ParsedCustomerRequest`. It then runs a catalog-matching pass using the same agent with temporary instructions and structured `CatalogMatch` output. Python validates match coverage and product names, checks catalog sales units, and routes the normalized request through `dispatch_request`.

The specialist agents are:

- **Inventory Agent:** evaluates a requested product and lists available inventory. Available stock accounts for active reservations. Supplier dates are estimates based on `get_supplier_delivery_date`.
- **Quotes Agent:** searches historical quote data and calculates a deterministic quote. The implementation treats catalog `unit_price` as acquisition cost, adds a 25% markup, and applies a 5% discount at 500 units or a 10% discount at 1,000 units per product.
- **Sales Agent:** evaluates deadlines, inventory, reservations, and cash before calling `fulfill_order`. The tool records direct sales atomically, supports order IDs for idempotent retries, or creates a pending order with stock and cash reservations when replenishment is required.
- **Reporting Agent:** answers cash, inventory, and financial-report questions using the starter helper functions.

`process_pending_orders(as_of_date)` runs from the scenario harness before each customer request. It records due supplier receipts, then records the sale and releases reservations when all lines are available. Replenishment receipts, sales, reservation updates, and order-result changes use a database transaction.

The workflow diagrams currently in the workspace are [`diagrams/diagram.png`](diagrams/diagram.png) and [`diagrams/workflow.png`](diagrams/workflow.png).

## Data and business rules

- `paper_supplies` is the catalog source. Each product has a canonical name, category, acquisition `unit_price`, and sales unit. Some specialty products have an unspecified unit and must not be quoted or sold until clarified.
- Duplicate product lines are consolidated before stock assessment and quoting.
- Bulk discounts apply to each product's consolidated quantity.
- A purchase is rejected when the delivery deadline is infeasible or the replenishment cost exceeds unreserved cash.
- If replenishment is feasible, the system reserves existing stock and the funds needed for the shortage. It records neither a purchase nor a sale until the supplier's estimated arrival date.
- `fulfilled` means that the sale transaction was recorded in the simulation. It does not mean the goods were physically shipped or delivered to the customer.
- Unsupported items and ambiguous specifications must be retained in the structured request and must block execution until resolved. No partial order should silently drop a line.

## Evaluation

The supplied scenario file has 20 customer requests. Evaluation must use both `test_results.csv` and the console log because a request can initially be pending and later become fulfilled as simulated dates advance. The final order table is the source of truth for completed orders.

Two full evaluation snapshots were observed while developing the catalog resolver:

| Resolver iteration | Completed | Pending at end | Rejected | Clarification / no order | Interpretation |
|---|---:|---:|---:|---:|---|
| Earlier permissive resolver | 10 | 1 | 6 | 3 | Met the numeric threshold, but some extracted lines were silently omitted or mapped to the wrong catalog item (including balloons/tickets and package units). These results are not evidence of correct fulfillment. |
| Exact-name resolver | 0 | 0 | 0 | 20 | Prevented unsafe substitutions, but was too strict for ordinary synonyms and descriptive wording. It did not meet the three-order completion requirement. |

The current implementation uses a semantic catalog-matching pass with strict programmatic coverage and unit checks to balance these outcomes. A fresh full evaluation against `quote_requests_sample.csv` is still required before claiming the rubric's result. The latest `test_results.csv` and `output.txt` were not present in the workspace when this report was written, so no current-run counts are asserted here.

Known limitations include the LLM's semantic match judgment, intentionally conservative handling of color/size/material claims not represented in the catalog, and supplier delivery being an estimate rather than a confirmed external order. The model should not be allowed to weaken the deterministic checks for match coverage, canonical catalog names, units, cash, deadlines, or database writes.

## Strengths

- Structured Pydantic requests keep intent, quantities, units, dates, and order IDs explicit.
- Pricing, stock, delivery, and cash calculations are implemented in deterministic tools rather than delegated to free-form model arithmetic.
- Pending orders reserve resources, process supplier receipts by simulated date, and can be retried by stable order ID.
- Transactional writes prevent a partially recorded multi-line sale when a database operation fails.
- The design stays within the five-agent limit and includes the required inventory, cash, and financial-report helpers.

## Further improvements

1. **Improve catalog data and matching tests.** Add reviewed aliases and supported attributes to the canonical catalog, then test every scenario's original line against its proposed match. Keep ambiguous product properties and unsupported goods as clarification or rejection results.
2. **Strengthen concurrent reservation safety.** The current assessment-then-write sequence is safe for the sequential simulator but can race if simultaneous requests inspect the same stock or cash. Perform availability checks and reservation writes under a serialized database transaction, and add a concurrent-request test.
3. **Persist evaluation evidence.** Export original request, structured extraction, catalog matches, initial response, final status, and final reason. Preserve the console log and CSV from the same run so the report can be reproduced.
4. **Persist accepted pricing.** Store the accepted quote with each pending order so later catalog or discount-policy changes cannot alter the sale amount at fulfillment.

## Running and submitting

Set `UDACITY_OPENAI_API_KEY` and the configured model name for the Vocareum-compatible endpoint, install the dependencies from `requirements.txt`, and run `project_starter.py` from the project directory. The scenario evaluation makes model calls and writes `test_results.csv`; retain that file and the console output from the same run for final evaluation evidence.
