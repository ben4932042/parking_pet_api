# Search Feedback Workflow

Use this workflow when working on search quality, search flow optimization, or user feedback analysis.

For the full optimization loop and priority order, see `docs/search/workflow-optimization.md`.

## Standard Entry Point

Retrieve search feedback through the reusable project script:

```bash
poetry run python interface/script/get_user_feedback.py
```

Do not issue ad hoc MongoDB queries when this script already covers the need.

## Supported Filters

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

## Output Contract

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

## Extension Rules

If new retrieval behavior is needed:

1. Extend the domain repository contract.
2. Extend the MongoDB repository implementation under `infrastructure/mongo`.
3. Extend `interface/script/get_user_feedback.py`.
4. Keep unit tests stable and update affected test doubles in the same change.

Do not bypass the existing project layering for one-off data access.
