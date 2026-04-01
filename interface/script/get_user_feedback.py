import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.mongo import MongoDBClient
from infrastructure.mongo.search_feedback import SearchFeedbackRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query search feedback documents from MongoDB."
    )
    parser.add_argument("--query-contains", help="Filter feedback query text.")
    parser.add_argument("--reason-contains", help="Filter feedback reason text.")
    parser.add_argument(
        "--response-type",
        choices=[
            "semantic_search",
            "keyword_search",
            "hybrid_search",
            "fallback_search",
        ],
        help="Filter by response type.",
    )
    parser.add_argument("--user-id", help="Filter by user id.")
    parser.add_argument("--source", help="Filter by source.")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of feedback rows to return. Capped at 200.",
    )
    return parser.parse_args()


def build_stdout_payload(items: list[dict]) -> list[dict]:
    return [
        {
            "query": item["query"],
            "response_type": item["response_type"],
            "preference": item["preferences"],
            "reason": item["reason"],
        }
        for item in items
    ]


async def main() -> None:
    args = parse_args()
    client = MongoDBClient()
    repo = SearchFeedbackRepository(client=client, collection_name="search_feedback")

    try:
        items = await repo.list_feedback(
            query_contains=args.query_contains,
            reason_contains=args.reason_contains,
            response_type=args.response_type,
            user_id=args.user_id,
            source=args.source,
            limit=args.limit,
        )
        payload = [item.model_dump(by_alias=True) for item in items]
        stdout_payload = build_stdout_payload(payload)
        print(json.dumps(stdout_payload, ensure_ascii=False, indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
