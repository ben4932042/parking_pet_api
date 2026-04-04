# User Feedback Workflow

## Scope

Use this workflow when retrieving and analyzing user feedback during development.

Feature-specific optimization rules should live in their own feature folders.

## When To Read This Doc

Read this document when:

- collecting user feedback during development
- inspecting recurring search quality issues
- extending the shared feedback retrieval script
- deciding whether a feature-specific workflow should start from recent feedback

Read the relevant feature workflow after this when the feedback is being used to tune a specific area such as search.

## Entry Points

- Shared feedback script: `interface/script/get_user_feedback.py`
- Feedback repository contract: `domain/repositories/search_feedback.py`
- MongoDB implementation: `infrastructure/mongo/search_feedback.py`
- Search optimization workflow: `docs/search/workflow-optimization.md`

## Rules

### Standard Entry Point

Retrieve search feedback through the reusable project script:

```bash
poetry run python interface/script/get_user_feedback.py
```

Do not issue ad hoc MongoDB queries when this script already covers the need.

### Supported Filters

The script supports these filters:

```bash
poetry run python interface/script/get_user_feedback.py --query-contains 青埔
poetry run python interface/script/get_user_feedback.py --reason-contains 分類
poetry run python interface/script/get_user_feedback.py --response-type semantic_search
poetry run python interface/script/get_user_feedback.py --user-id <user-id>
poetry run python interface/script/get_user_feedback.py --source user
poetry run python interface/script/get_user_feedback.py --limit 50
```

Filters can be combined.

### Output Contract

The script prints standardized JSON to stdout.

Each item includes only:

- `query`
- `response_type`
- `preference`
- `reason`

Example:

```json
[
  {
    "query": "想吃點心",
    "response_type": "semantic_search",
    "preference": [
      {
        "key": "primary_type_preference",
        "label": "dessert_shop"
      }
    ],
    "reason": "結果不相關"
  }
]
```

### Extension Rules

If new retrieval behavior is needed:

1. Extend the domain repository contract.
2. Extend the MongoDB repository implementation under `infrastructure/mongo`.
3. Extend `interface/script/get_user_feedback.py`.
4. Keep unit tests stable and update affected test doubles in the same change.

Do not bypass the existing project layering for one-off data access.

## Validation

- Keep unit tests stable when the feedback retrieval contract changes.
- If the repository contract or script output changes, update all affected doubles, fixtures, and script-level expectations in the same change.
- If the change affects feature workflows that depend on feedback fields, update those docs in the same change.

## Related Files

- `docs/search/workflow-optimization.md`
- `interface/script/get_user_feedback.py`
- `domain/repositories/search_feedback.py`
- `infrastructure/mongo/search_feedback.py`
- `tests/unit/infrastructure/test_mongo_search_feedback.py`
