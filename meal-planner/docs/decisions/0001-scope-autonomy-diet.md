# 0001: Scope, autonomy, and dietary rules

- **Status:** Draft
- **Date:** 2026-10-10

## Context

Two people share the cooking. One eats meat and has health and fitness goals; the other is vegetarian. Weeknight time is limited. The agent plans meals through chat. Every decision below sets how much the agent does on its own versus how much the user reviews.

## Decisions

### 1. Scope

The agent plans **dinners, plus extra portions cooked on purpose to become the next day's lunch.**

Breakfasts and lunches that aren't leftovers are out of scope.

### 2. Autonomy

The default is to keep a human in the loop. Each action gets one of three policies:

- **auto:** the agent acts without asking.
- **notify:** the agent acts and immediately shows what it did.
- **approve:** the agent proposes, and the user applies it.

| Action | Policy | Why |
|---|---|---|
| Search recipes, read memory, draft or revise a plan | auto | Read-only or easy to undo |
| Save a newly learned preference | notify | Early on, the user wants to see what the agent is learning while it learns it |
| Change health targets or diet rules | approve | The agent may suggest adjustments based on feedback, but never applies them itself |
| Forget or delete a memory | approve | Deletion can't be undone, and the user wants to see what is being learned |
| Finalize the week's plan and grocery list | approve | The user reviews every plan until the agent has a track record |

### 3. Partner's diet rule

The partner is **lacto-ovo vegetarian**:

- **Allowed:** eggs and dairy, including cheese.
- **Forbidden:** meat, poultry, fish, seafood, and anything derived from them. That includes:
  - meat, poultry or fish stock and broth
  - fish sauce, oyster sauce, Worcestershire sauce, anchovies and anchovy paste
  - dashi and bonito
  - gelatin, lard, suet
  - shrimp paste
  - Caesar dressing

## Options considered

- **Scope:**
  - Dinners only: simplest, but loses the leftover-lunch value.
  - Every meal: complete, but triples the planning work before the basics are proven.
- **Autonomy:**
  - Full autonomy: fast, but the user can't see or correct what the agent learns.
  - Approve everything: safe, but too much friction to use every week.

  The three-level policy sits between the two.

## Consequences

- **Data model:** a dinner has to be linked to the lunch portions it produces, including who eats each portion.
- **Permissions:** the system needs three levels (auto, notify, approve). The common two (auto, ask) are not enough.
- **Diet rule:** this is a hard check in code, backed by an ingredient denylist. The model also flags hidden animal products the list doesn't know about.
- **Food safety:** leftovers need a "use within N days" rule.
- **Finalizing:** approval adds friction every week. It also builds the record of good plans needed to relax the policy later.

## Revisit when

- Evals show plans pass every must-have criterion reliably over several weeks. At that point, consider moving "finalize plan" to notify.
- The memory log shows saved preferences are consistently correct. At that point, consider moving "save preference" to auto.
