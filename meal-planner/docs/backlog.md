# Backlog

Ideas that came up during design but aren't assigned to a stage yet. Each entry notes the concept it would exercise.

## Inventory

- **Pantry staples kept separately.** Track long-lasting dry goods apart from perishables: flour, rice, vinegar, spices, each with an approximate quantity and expiry date. Perishables are worked out fresh each week. Pantry staples rarely change, so they persist and the agent only confirms them occasionally. *Concept: data that changes at different rates needs different memory strategies.*
- **Receipt upload.** The user photographs or uploads grocery receipts. The model reads them and pulls out structured line items (item, quantity, price, date). Those line items replace the assumption that the grocery list was bought exactly as written. *Concepts: observations beat assumptions; image input; structured extraction.*
- **Spending tracking.** Use receipt line items to report weekly grocery spend and cost per meal. *Concept: once you collect real data, more features can use it. Watch for scope creep.*

## Learning from patterns

- **Time budgets that adapt.** If a weekday's budget is repeatedly overrun or the meal gets skipped, propose a new budget for that day (approval policy). *Concept: memory consolidation. Patterns in what happened turn into updated facts in the profile.*
- **Better cook-time estimates.** Use logged actual cook times to adjust the model's estimates for similar recipes.

## Integrations

- **Calendar.** A calendar MCP server, so the agent can read busy evenings and events with dinner provided, instead of being told.
- **Training plan import.** Bring in training phase and day types from a training app or plan export.
