# 0003: Health baseline and per-person targets

- **Status:** Accepted
- **Date:** 2026-10-11

## Context

Both people have health and fitness goals. An agent that learns preferences drifts toward whatever gets rated highly. Without a fixed baseline, a run of five-star comfort food slowly reshapes every plan. The plan therefore needs a health baseline that learned preferences cannot wear down.

## Decisions

### 1. The baseline is procedural memory that only the household can edit

- **Where it lives.** The baseline is `docs/spec/health-baseline.md`, a versioned file. It is loaded into the agent's system prompt, and its Must rules are enforced by validators.
- **Who can change it.** The agent has no tool that can write to it. Only the household edits it, by editing the file. The agent may suggest changes in conversation.
- **Why the distinction matters.** Learned preferences are memory the agent writes. The baseline is memory the household writes. Keeping the two apart is what makes the baseline a real guardrail.

### 2. Priority order

When rules conflict, they are applied in this order:

1. Safety Musts.
2. The health baseline.
3. Learned preferences.
4. Novelty.

A preference may bring a dish back. It may not break a baseline rule.

### 3. Baseline Musts

Four rules are Musts:

| Rule | Requirement |
|---|---|
| H1 | Every portion has a protein source |
| H2 | Every dinner has a vegetable component |
| H3 | Processed meat at most once a week |
| H4 | Deep-fried at most once a week |

All four can be checked mechanically and can almost always be met. The rest of the baseline is Should.

### 4. Per-person targets

- **Each person has a profile.** Each profile has optional nutrition targets: a daily protein target and eating occasions per day.
- **The partner's targets are blank for now.** Until they are filled in, the baseline alone applies to the partner.
- **Who can change targets.** Target changes follow the approval policy in decision 0001.

## Consequences

- **The vegetarian base must stand on its own.** In a "vegetarian base plus a meat side" meal, the base has to meet the vegetarian person's protein needs without the meat (rule H5). This rules out "the partner gets the sides".
- **Some Musts depend on model labels.** The code reads tags the model assigns: protein source, vegetable component, cooking method. Evals test the tagging as well as the code.
- **Decision 0002 changes.** The protein criterion now applies to each person who has a target, not only one person.
