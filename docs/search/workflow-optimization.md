# Search Optimization Workflow

Use this workflow when improving search relevance, intent parsing, or feedback-driven search behavior.

This project should optimize search in this order:

1. Prompt optimization first
2. Keyword / rule supplementation second
3. Larger retrieval or ranking changes last

The goal is to keep improvements cheap, explainable, and easy to regression-test before changing deeper system behavior.

## Optimization Principles

- Start from real user feedback, not intuition alone.
- Prefer fixing intent interpretation before changing database behavior.
- Treat prompt changes as the default lever for semantic-search quality.
- Use keyword and rule updates only to cover stable, high-confidence patterns that the prompt should not infer loosely.
- Avoid broad keyword expansion that can silently over-match many unrelated queries.

## Standard Loop

### 1. Retrieve feedback

Always begin with the shared feedback script:

```bash
poetry run python interface/script/get_user_feedback.py --limit 100
```

Useful focused queries:

```bash
poetry run python interface/script/get_user_feedback.py --reason-contains 分類
poetry run python interface/script/get_user_feedback.py --query-contains 青埔
poetry run python interface/script/get_user_feedback.py --response-type semantic_search
```

### 2. Cluster failure patterns

Group feedback into a small number of recurring buckets, for example:

- address vs landmark confusion
- category misclassification
- pet-feature extraction mistakes
- quality / open-now interpretation mistakes
- typo normalization mistakes
- keyword fallback behavior gaps

Do not optimize directly from one isolated query unless it represents a stable pattern.

### 3. Choose the cheapest correct lever

Use this decision order:

#### Prompt first

Choose prompt updates when:

- the model understands the query inconsistently
- the failure is about instruction priority or boundary definition
- the fix is about address vs landmark separation
- the fix is about when to abstain instead of guessing
- the query should remain flexible rather than hard-coded

Typical files:

- `infrastructure/prompt/search.py`

#### Keyword / rule second

Choose keyword or rule updates when:

- the pattern is frequent and linguistically stable
- the business meaning is deterministic
- a negative phrase should override a positive substring
- a known place term should always map the same way
- a compact rule can avoid unnecessary LLM ambiguity

Typical files:

- `infrastructure/google/search.py`

Examples:

- adding a stable landmark keyword
- adding a negative phrase like `不需要推車`
- protecting against negated category matches like `不是公園`

#### Larger search changes last

Choose repository, ranking, or retrieval changes only when:

- prompt and rule updates cannot address the issue safely
- the problem is clearly about recall, ranking, or retrieval architecture
- the improvement requires new signals rather than better interpretation

Typical files:

- `application/property.py`
- `infrastructure/mongo/property.py`
- retrieval architecture modules added in the future

## Prompt-First Checklist

Before adding a keyword or rule, check whether the issue can be solved by tightening prompts:

- Is the model missing a boundary that should be explicit?
- Is it confusing landmark with address?
- Is it over-guessing category or feature?
- Should the prompt include a stronger abstain rule?
- Should an example be added for this pattern?

If yes, update the prompt first and add or update regression tests.

## Keyword / Rule Checklist

Only add rule-based behavior when all of the following are true:

- the phrase has stable meaning
- the rule is narrow and low-risk
- the rule improves multiple likely queries, not one one-off sample
- the rule will not create many false positives
- a unit test can pin the behavior clearly

When adding rules:

- prefer narrow exact phrases over broad fuzzy expansions
- support negation explicitly when relevant
- make sure rule-based behavior does not contradict prompt instructions
- update tests for both the positive and negative cases

## Regression Expectations

Every search optimization change should include regression coverage close to the behavior being changed.

Common targets:

- `tests/unit/application/test_property_search_pipeline.py`
- `tests/unit/application/test_property_search.py`
- API-layer tests when response semantics change

Minimum expectation:

- one test that reproduces the original failure
- one test that protects a nearby non-target case from regression

## Suggested Working Sequence

For each optimization batch:

1. Pull recent feedback with the shared script.
2. Summarize the top recurring error patterns.
3. Decide which issues are prompt-first.
4. Implement prompt updates and regression tests.
5. Re-check whether any remaining gaps need rule-based keyword supplementation.
6. Implement only the smallest safe rules.
7. Run the relevant search tests, then the full unit suite if shared behavior changed.
8. Record the reasoning in the PR or work summary so future tuning has context.

## Current Project Preference

For this repository:

- prompt optimization is the primary strategy
- keyword supplementation is a secondary strategy
- keyword search itself is currently fallback behavior, so avoid over-investing in it unless feedback clearly points there

This preference should guide future search-quality work unless product requirements change.
