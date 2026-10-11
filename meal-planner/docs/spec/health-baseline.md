# Health baseline

These are the rules every plan follows, for both people, whatever their preferences. The agent reads this file but cannot change it. Only the household changes it, by editing the file. The agent may suggest changes in conversation.

The numbers are starting values taken from general dietary guidance, not personal medical advice. Adjust them with a professional if needed.

## Priority order

When rules conflict, the higher one wins:

1. **Safety Musts.** The vegetarian rule, allergens, and food safety (`good-week.md`).
2. **This baseline.**
3. **Learned preferences.** Ratings, favorites, and dislikes from memory.
4. **Novelty.** Requests like "try something new this week".

A preference can bring a dish back. It can't break a baseline rule. If a favorite conflicts with the baseline, change the dish (for example, oven-fry instead of deep-fry) rather than relax the rule.

## Rules

Each rule applies per portion unless it says otherwise.

| # | Rule | Measured by | Type |
|---|---|---|---|
| H1 | Every person's portion has a real protein source. For the vegetarian, that means legumes, tofu, tempeh, seitan, eggs, or dairy. | A protein-source tag on each portion | Must |
| H2 | Every dinner includes at least one substantial vegetable component. | A vegetable-component tag | Must |
| H3 | Processed meat (bacon, sausage, ham, deli meats, hot dogs) appears at most once a week. | Weekly count | Must |
| H4 | Deep-fried dishes appear at most once a week. | Weekly count of the cooking-method tag | Must |
| H5 | In a vegetarian-base-plus-meat-side meal, the base on its own meets the vegetarian person's per-meal protein target. The meat side is not counted. | Grams of protein in the vegetarian person's portion | Should |
| H6 | About half the plate is vegetables. | At least about 150 g of non-starchy vegetables per portion | Should |
| H7 | Fiber comes from whole grains or legumes. | At least about 8 g of fiber per portion | Should |
| H8 | Sodium stays in check. | At most about 800 mg per portion | Should |
| H9 | Legumes appear at least three times a week. | Weekly count | Should |
| H10 | The vegetarian diet covers the nutrients it most often runs short on. | Weekly LLM-judge check | Should |

H10 means:
- iron sources paired with vitamin C;
- B12 from eggs or dairy;
- omega-3 sources such as walnuts, flax, or chia;
- a mix of protein sources across the week.

## How the rules are checked

- **Inputs come from the model.** The Must checks (H1–H4) run in code, but they read tags the model assigns: protein source, vegetable component, cooking method. A check is only as reliable as its inputs. The evals in Stage 7 test the tagging, not just the counting.
- **Nutrient numbers come later.** H5–H8 need real nutrient values. They are scored once the USDA nutrition server exists (Stage 5). Until then, the agent labels these numbers as estimates.
