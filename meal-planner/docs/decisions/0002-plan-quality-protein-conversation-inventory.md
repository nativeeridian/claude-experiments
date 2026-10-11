# 0002: Plan quality rules, protein, conversation style, inventory

- **Status:** Accepted
- **Date:** 2026-10-11

## Context

Writing the sample conversations and the definition of a good week brought up four issues:

1. A daily protein target doesn't fit an agent that only plans dinner and leftover lunch.
2. The desired Sunday reply asked three questions and produced no plan.
3. The re-plan flow needs to know what food is already in the house.
4. Eating out needs to be part of the plan.

## Decisions

### 1. Must vs. Should

A rule is a **Must** only if it meets all three tests:

- code can check it with a clear yes or no;
- a plan can almost always satisfy it;
- breaking it is expensive.

A Must that often can't be satisfied makes the agent loop forever: save, rejected, retry. The six Musts and seven Shoulds are listed in `docs/spec/good-week.md`. The nightly time budget is a Must even though it compares two estimates. Logged actual cook times will make those estimates more accurate over time.

### 2. Protein uses a per-meal target, scored as a Should

- **The target.** Planned meals aim for a per-meal protein target on the user's plate. The per-meal target is the daily target divided by the number of eating occasions per day. Both numbers live in the profile.
  - This makes the planned share follow from how the user actually eats, not an arbitrary percentage.
  - It also matches common sports-nutrition guidance: spread protein across meals, roughly 0.25–0.4 g per kg of body weight per meal, rather than loading one meal.
- **Measurement.** Protein for each meal is computed from nutrition data (from Stage 5 on). A weekly scorecard reports two things: the share of planned meals that hit the per-meal target, and the planned protein per day against the daily target.
- **Why a Should.** Nutrition values are estimates, and eating out or skipped meals are outside the agent's control.
- **Changing the target.** It adapts to fitness goals by proposal only. When the training phase changes (a marathon build, recovery, a strength block), the agent may propose a new daily target or a carbohydrate emphasis for certain day types. The user approves the change (decision 0001).
- **Partner.** Each person has their own profile with optional targets. The partner's targets are left blank for now, and until they are filled in only the health baseline applies to the partner (decision 0003).

### 3. Propose first, then ask

On a planning request, the agent:

1. drafts a plan from memory;
2. states the assumptions it made;
3. asks **at most two** questions, and only about things memory can't answer (a new training phase, a new recipe, an unusual week).

### 4. Inventory is worked out from the plan

The system assumes the finalized grocery list was bought. Logging a meal as cooked uses up its ingredients. The user reports exceptions: "defrosted the chicken", "the spinach went bad", "bought extra rice". Each ingredient category has a shelf life, which lets the agent flag items that need using soon.

### 5. Eating out is a meal-slot type

An eating-out slot has no groceries and unknown macros. Sometimes it produces leftovers, which can be logged as a lunch. Aiming for two or more eating-out nights a week is a Should. The agent proposes Friday and Saturday by default.

## Options considered

- **Protein:**
  - A hard 118 g/day Must. Rejected: the agent can't control breakfast and snacks.
  - Display only. Rejected: it isn't measurable against goals.
  - Tracking the whole day. Rejected: too much daily logging.
- **Conversation:**
  - Ask first. Rejected: too slow every week.
  - Ask only what changed. Close to the chosen option. "Propose, then ask" also guarantees a plan arrives in the first reply.
- **Inventory:**
  - A pantry list the user maintains. Rejected: too much work.
  - No inventory. Rejected: it loses the "use it before it goes bad" feature.

## Consequences

- **Profile fields.** The profile needs the daily protein target, eating occasions per day, a training schedule by day type, and the current training phase.
- **Protein before Stage 5.** Until the nutrition server exists, protein values are model estimates and are labelled as estimates.
- **Inventory drift.** The worked-out inventory will drift from the real fridge. The agent should confirm before relying on an item. For example: "You should still have the chicken from Tuesday, right?"
- **System prompt.** The two-question limit and the "state your assumptions" rule go into the system prompt.
