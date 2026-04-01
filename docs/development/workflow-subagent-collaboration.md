# Sub-Agent Collaboration Workflow

## Scope

Use this workflow when a development task benefits from repeated collaboration between:

- a developer-focused agent
- a QA-focused agent
- a coordinating primary agent

This workflow is especially useful for search tuning, regression-focused bug fixing, and changes where test coverage should lead implementation.

## When To Read This Doc

Read this document when:

- you want to split a task between implementation and test design
- you want to run a repeatable QA -> developer -> validation loop
- you want a primary agent to coordinate sub-agents instead of handling all work alone

Read the relevant feature workflow before executing the loop for that feature.

Examples:

- search work: `docs/search/workflow-optimization.md`
- property creation or management work: the corresponding file under `docs/property/`

## Entry Points

- Feature docs under `docs/`
- Main implementation files for the feature being changed
- Existing unit and integration tests closest to the behavior under discussion

## Rules

### Role split

Use these responsibilities unless the task clearly needs a different split:

- QA agent
  - propose test cases
  - identify edge cases and regressions
  - call out contract ambiguities between docs, tests, and implementation
- Developer agent
  - map the runtime flow
  - identify the smallest safe implementation or test change
  - avoid broad refactors unless the coordinating agent explicitly asks for them
- Primary agent
  - read the required docs first
  - choose the next batch
  - integrate results
  - make edits
  - run validation
  - decide whether another loop is needed

### Standard loop

Run the workflow in this order:

1. Read the relevant feature docs and locate the active code path.
2. Ask the QA agent for a compact test matrix, highest-risk regressions, and the next few concrete cases worth adding.
3. Ask the Developer agent for the execution flow, fragile points, and the smallest safe change to make first.
4. Let the primary agent select one small batch from those recommendations.
5. Implement that batch before opening more scope.
6. Run the relevant tests.
7. If the result is still incomplete, start another loop with the updated context.

### Batch size

Keep each loop small.

Prefer one of these per round:

- one new failing behavior reproduced by tests
- one small prompt or rule adjustment
- one service-level behavior fix
- one response-contract clarification

Do not mix unrelated search, API, and persistence changes in the same round unless they are tightly coupled.

### Source of truth

If docs, tests, and implementation disagree:

1. make the disagreement explicit
2. choose whether code or docs should change
3. encode the chosen behavior in tests

Do not leave the loop with the ambiguity unresolved.

### Search-specific preference

When using this workflow for search:

1. prefer prompt optimization first
2. use rules second
3. make deeper retrieval or ranking changes last

Keep this aligned with `docs/search/workflow-optimization.md`.

## Validation

Every loop should end with validation that matches the change scope.

Minimum expectation:

- run the nearest unit tests for the changed behavior
- run the broader unit suite if shared contracts changed

If search logic or prompts changed:

- run the relevant search unit tests
- run `tests/integration/test_search_conditions_api.py`

If validation fails:

- do not stop at reporting the failure
- identify whether the issue is a test expectation problem, an implementation bug, or a doc mismatch
- fix it or record the blocker clearly

## Related Files

- `docs/documentation/architecture.md`
- `docs/development/workflow-user-feedback.md`
- `docs/search/workflow-optimization.md`
- `tests/unit/application/test_property_search_pipeline.py`
- `tests/unit/application/test_property_search.py`
- `tests/integration/test_search_conditions_api.py`
