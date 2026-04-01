import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.mongo import MongoDBClient


SEARCH_FIELD_UNSETS = {
    "search_text": "",
    "search_embedding": "",
    "embedding_version": "",
    "embedding_model": "",
    "embedding_updated_at": "",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove deprecated vector-search fields from property documents."
    )
    parser.add_argument(
        "--collection",
        default="property_v3",
        help="MongoDB collection name.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of documents to clean. 0 means no limit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many documents would be updated without modifying data.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    client = MongoDBClient()
    collection = client.get_collection(args.collection)

    selector = {
        "$or": [{field: {"$exists": True}} for field in SEARCH_FIELD_UNSETS.keys()]
    }

    try:
        if args.dry_run:
            matched = await collection.count_documents(selector)
            print(
                json.dumps(
                    {
                        "status": "dry_run",
                        "collection": args.collection,
                        "matched": matched,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return

        if args.limit > 0:
            updated = 0
            cursor = collection.find(selector, {"_id": 1}).limit(args.limit)
            async for doc in cursor:
                await collection.update_one(
                    {"_id": doc["_id"]},
                    {"$unset": SEARCH_FIELD_UNSETS},
                )
                updated += 1
        else:
            result = await collection.update_many(
                selector,
                {"$unset": SEARCH_FIELD_UNSETS},
            )
            updated = result.modified_count

        print(
            json.dumps(
                {
                    "status": "completed",
                    "collection": args.collection,
                    "updated": updated,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
