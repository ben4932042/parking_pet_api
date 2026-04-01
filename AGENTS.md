# AGENTS.md

Repository-wide instructions for coding agents working in this project.

## Index

- [Testing Rules](#testing-rules)
- [Search Feedback Workflow](#search-feedback-workflow)
- [Search Optimization Priority](#search-optimization-priority)

## Related Docs

- `docs/search/workflow-feedback.md`
- `docs/search/workflow-optimization.md`

## Testing Rules

- Any code change must keep unit tests stable.
- If an interface, abstract class, protocol, shared dependency contract, fixture, or repository API changes, update all related unit-test doubles, stubs, fakes, and mocks in the same change.
- Do not stop after running only targeted tests when the change can affect shared contracts; run the relevant full unit test suite before finishing.
- A task is not complete if unit tests are broken.

## Search Feedback Workflow

- When a task involves search quality, search flow optimization, or user feedback analysis, retrieve search feedback through the reusable project script instead of issuing ad hoc MongoDB queries.
- Use `poetry run python interface/script/get_user_feedback.py` to fetch search feedback from MongoDB.
- The script prints standardized JSON to stdout and includes only:
  - `query`
  - `response_type`
  - `preference`
  - `reason`
- Use the supported script filters when needed:
  - `--query-contains`
  - `--reason-contains`
  - `--response-type`
  - `--user-id`
  - `--source`
  - `--limit`
- If new feedback retrieval behavior is needed, extend the domain repository, MongoDB repository, and script within the existing project architecture instead of bypassing them.

## Search Optimization Priority

- When optimizing search, prefer prompt optimization first and keyword or rule supplementation second.
- Use real user feedback to decide which path to take.
- Only move to repository, ranking, or larger retrieval changes after prompt and rule-based fixes are clearly insufficient.
- Follow `docs/search/workflow-optimization.md` for the standard optimization loop.
