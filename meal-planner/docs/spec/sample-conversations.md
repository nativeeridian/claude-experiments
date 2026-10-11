# Sample conversations

These are written by the user and kept word for word. They describe how the agent should feel to use, not exact wording to copy. Decision 0002 changes one behaviour shown here: the agent proposes a plan first, then asks at most 1–2 questions.

## 1. Planning the week (Sunday)

**User:**
> For this upcoming week, I want to try a couple of new recipes. Last week's baked tofu was great so I want you to remember that as a key protein type to mix into future recipes. Tonight I want to focus on creating something that will last for a couple of days with some kind of asian fusion and twist.

**Agent (desired):**
> Making a note about the baked tofu - that was a special recipe from X source and one that will be worth repeating into other dishes given how versatile it is. What about the tofu did you like? This will help me understand your preferences better.
>
> For the asian fusion and twist, what specific flavors did you want to bring into this kind of recipe? Sweet and sour? or something else on your mind?
>
> Keeping consistent with your fitness goals for the week, I want to understand what training plans you have to better align this meal has anything changed since your recent marathon?

## 2. Re-planning midweek

**User:**
> Turns out I have an event to attend tonight with dinner provided so I won't be needing to cook. That being said, I already defrosted some items and don't want them to go to waste, is there a quick recipe I could plan on cooking or would it be fine to use the food tomorrow? Additionally, I want to re-think the weekend meals, I heard about this new recipe I want to experiment with but would like to align it to the existing groceries I have so I do not waste anything.

**Agent (desired):**
> Not a problem we can certainly save those items for later, just confirm for me they were the things for the baked chicken risotto.
>
> For this weekend, tell me more about this new recipe? Knowing your current grocery stock, this week you likely have X items that will go bad soon that we should try to incorporate into this new recipe.

## 3. Feedback after a meal

**User:**
> This latest orzo one pan meal was great - the pesto sauce was a great addition and it only took 30-35minutes to cook in total, this is one to save for the books. My partner also loved it.

**Agent (desired):**
> Glad that you liked it! Given your feedback and the (X memories here) on recent weeks, I figured this would be a slam dunk. I will save this one to incorporate moving forward. How frequently do you wish to see this specific recipe appear in the rotation? And are there any specific things about it you want me to keep in mind about other recipes moving forward?

## Requirements these conversations imply

Reading rule: nouns become data, verbs become tools, and each question the agent asks points at something missing from its memory.

| From the conversation | Requirement | Stage |
|---|---|---|
| "remember baked tofu… from X source" | The agent saves preferences (notify policy); recipes record where they came from | 2, 4 |
| "since your recent marathon" | Training phase is kept in memory; targets can be proposed for change but not applied without approval | 4 |
| "will last for a couple of days" | One dinner can produce leftover portions that fall inside the leftover window | 2 |
| "dinner provided tonight" | A planned slot can be changed midweek to eating out or skipped | 2 |
| "defrosted… groceries I have… will go bad soon" | Inventory, worked out from the plan, with shelf life per item | 2, 4 |
| "confirm they were for the chicken risotto" | Each ingredient is linked to the planned meal it was bought for | 2 |
| "new recipe I heard about" | Import a recipe the user brings (pasted text now, web fetch later) | 5 |
| "partner also loved it" | Ratings are stored separately for each person | 4 |
| "30-35 minutes" | Actual cook time is logged and corrects future estimates | 4 |
| "save for the books… how frequently in rotation?" | Favorites have a target rotation frequency | 4 |
| "Given your feedback and X memories…" | Each planned meal stores why it was chosen, so the agent can explain the choice later | 2, 4 |
