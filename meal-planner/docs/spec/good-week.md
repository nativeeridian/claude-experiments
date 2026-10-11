# What a good week plan looks like

This is the quality bar for a week's plan. It serves three purposes:

- The validators enforce the **Must** rules.
- The agent's system prompt states the **Should** rules.
- The evals in Stage 7 score plans against both.

| Type | What happens if a plan breaks it |
|---|---|
| **Must** | Code checks it before a plan is saved. A plan that breaks a Must is rejected, and the violations go back to the agent so it can fix the plan. |
| **Should** | The agent weighs it. Evals score it. A plan can still be saved while it misses a Should. |

Every plan must also pass the [health baseline](health-baseline.md) (rules H1–H10), which applies to both people. That file also sets the priority order when rules conflict.

Personal numbers (protein target, body weight, training schedule) live in the profile (`data/profile.json`, not committed to git). The criteria below refer to them by name.

## Criteria

| # | Criterion | Type | Values | How it's checked |
|---|---|---|---|---|
| 1 | Every dish the partner eats passes the vegetarian rule | Must | Lacto-ovo vegetarian; see decision 0001 | Code: ingredient denylist, plus the model flags hidden animal products |
| 2 | Each night's hands-on cooking time fits that night's budget | Must | Mon–Thu ≈ 45 min; Fri–Sun ≈ 75 min | Code: the model's time estimate ≤ that night's budget. Logged actual times correct the estimates over time. |
| 3 | No allergens or hard dislikes for either person | Must | From the profile | Code: ingredient check against the profile |
| 4 | Leftover lunches are eaten within the leftover window | Must | 1–2 days after cooking | Code: lunch date minus cook date |
| 5 | Every dinner and lunch says who is eating it | Must | — | Code: the plan's structure requires it |
| 6 | The grocery list covers every ingredient in the plan | Must | — | Code: the list is generated from the plan |
| 7 | Planned meals meet each person's per-meal protein target, for each person who has one | Should | Per-meal target = daily target ÷ eating occasions (see decisions 0002 and 0003) | Code: protein computed from nutrition data, scored weekly |
| 8 | Meat meals per week stay within your range | Should | 2–4 | Code: count |
| 9 | At least two eating-out nights are reserved | Should | ≥ 2, usually near or on the weekend | Code: count of eating-out slots |
| 10 | Variety | Should | No dish twice in a week; no main protein or cuisine more than 3 times | Code: counts |
| 11 | Prefer one shared base dish over cooking two separate meals | Should | Shared vegetarian dish, or a vegetarian base with meat on the side | Code: count of meal modes; the model makes the choice |
| 12 | Ingredients overlap across the week | Should | — | Code: overlap score across the week's ingredients |
| 13 | Plans draw on meals rated well and avoid meals rated low | Should | Ratings recorded per person | Eval: an LLM judge with access to the meal history |

## Starter eval cases

Each case below came out of the spec discussion. Each one becomes a Stage 7 eval scenario.

- **Hidden stock:** a "baked chicken risotto" served as a shared base with chicken on the side. The base must use vegetable stock; chicken stock must be rejected under criterion 1.
- **Hidden sauce:** a stir-fry with oyster sauce or fish sauce on the partner's plate must be rejected.
- **Time budget:** a 90-minute recipe on a Tuesday must be rejected under criterion 2.
- **Food safety:** leftovers planned for three days after cooking must be rejected under criterion 4.
- **Dinner provided:** "Dinner is provided tonight, and I already defrosted the ingredients." The agent moves those ingredients to a meal within their shelf life and doesn't waste them.
- **Favorites:** a well-rated favorite with a set rotation frequency comes back on schedule.
