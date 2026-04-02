import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from application.property_search.projection import build_property_alias_fields  # noqa: E402
from domain.entities.property import PropertyEntity  # noqa: E402
from infrastructure.mongo import MongoDBClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate property documents from property_v2 to property_v3."
    )
    parser.add_argument(
        "--source-collection",
        default="property_v2",
        help="Source MongoDB collection name.",
    )
    parser.add_argument(
        "--target-collection",
        default="property_v3",
        help="Target MongoDB collection name.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of documents to migrate. 0 means no limit.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip target documents that already exist.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=20,
        help="MongoDB cursor batch size.",
    )
    return parser.parse_args()


def _coerce_property_payload(raw_doc: dict) -> dict:
    payload = dict(raw_doc)
    payload.setdefault("_id", payload.get("place_id"))
    return payload


async def main() -> None:
    args = parse_args()
    client = MongoDBClient()
    source = client.get_collection(args.source_collection)
    target = client.get_collection(args.target_collection)

    migrated = 0
    skipped = 0
    failed = 0

    try:
        cursor = source.find({}).batch_size(args.batch_size)
        if args.limit > 0:
            cursor = cursor.limit(args.limit)

        async for raw_doc in cursor:
            payload = _coerce_property_payload(raw_doc)
            document_id = payload.get("_id")

            if args.skip_existing:
                existing = await target.find_one({"_id": document_id}, {"_id": 1})
                if existing is not None:
                    skipped += 1
                    continue

            try:
                property_entity = PropertyEntity(**payload)
                alias_fields = build_property_alias_fields(property_entity)

                payload.update(
                    {
                        **alias_fields,
                        "manual_aliases": payload.get("manual_aliases", []),
                    }
                )
                await target.replace_one({"_id": payload["_id"]}, payload, upsert=True)
                migrated += 1
            except Exception as exc:
                failed += 1
                print(
                    json.dumps(
                        {
                            "status": "failed",
                            "document_id": str(document_id),
                            "error": str(exc),
                        },
                        ensure_ascii=False,
                    ),
                    file=sys.stderr,
                )

        print(
            json.dumps(
                {
                    "status": "completed",
                    "source_collection": args.source_collection,
                    "target_collection": args.target_collection,
                    "migrated": migrated,
                    "skipped": skipped,
                    "failed": failed,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
