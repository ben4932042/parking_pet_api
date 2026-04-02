import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


STORE_NAMES = [
    "寵物公園–土城明德店",
    "寵物公園–台中大雅店",
    "寵物公園–三峽北大店",
    "寵物公園–高雄前金店",
    "寵物公園–台南佳里店",
    "寵物公園–南投埔里店",
    "寵物公園–草屯中興店",
    "寵物公園–台中沙鹿店",
    "寵物公園–板橋金門店",
    "寵物公園–龍潭北龍店",
    "寵物公園–三重仁愛店",
    "寵物公園–苓雅光華店",
    "寵物公園–台南健康店",
    "貓狗隊長–屏東內埔店",
    "寵物公園–高雄左營店",
    "貓狗隊長–桃園龜山店",
    "寵物公園–松山延吉店",
    "寵物公園–新竹建中店",
    "寵物公園–彰化鹿港店",
    "寵物公園–竹東快閃店",
    "寵物公園–台南善化店",
    "寵物公園–台南安南店",
    "寵物公園–新竹經國店",
    "寵物公園–嘉義友愛店",
    "寵物公園–楠梓楠新店",
    "寵物公園–桃園大有店",
    "寵物公園–高雄美術店",
    "寵物公園–新店民權店",
    "寵物公園–花蓮建國店",
    "寵物公園–台中陝西店",
    "寵物公園–彰化中央店",
    "寵物公園–桃園平鎮店",
    "寵物公園–台南新市店",
    "寵物公園–南投草屯店",
    "寵物公園–雲林虎尾店",
    "寵物公園–宜蘭羅東店",
    "寵物公園–彰化員林店",
    "寵物公園–南港二店",
    "寵物公園–台東中山店",
    "寵物公園–雲林斗南店",
    "寵物公園–台中太平店",
    "寵物公園–中山錦州店",
    "寵物公園–竹北福興店",
    "寵物公園–信義中坡店",
    "寵物公園–台中清水店",
    "寵物公園–新北泰山店",
    "寵物公園–屏東潮州店",
    "寵物公園–基隆信義店",
    "寵物公園–桃園龍安店",
    "寵物公園–高雄岡山店",
    "寵物公園–北屯軍功店",
    "寵物公園–大里成功店",
    "寵物公園–八德興豐店",
    "寵物公園–內湖康樂店",
    "寵物公園–台中西屯店",
    "寵物公園–台北安和店",
    "寵物公園–台北興隆店",
    "寵物公園–高雄新興店",
    "寵物公園–台南歸仁店",
    "寵物公園–台南新營店",
    "寵物公園–高雄楠梓店",
    "寵物公園–台中大里店",
    "寵物公園–台北南港店",
    "寵物公園–台南崑大店",
    "凱朵寵物-台中一心店",
    "寵物公園–汐止遠雄店",
    "寵物公園–大全聯南湖店",
    "寵物公園–台中北屯店",
    "寵物公園–苗栗竹南店",
    "寵物公園–前鎮瑞隆店",
    "寵物公園–林口仁愛店",
    "寵物公園–五甲二店",
    "寵物公園–內壢文化店",
    "寵物公園–仁武仁忠店",
    "寵物公園–林口中山店",
    "寵物公園–屏東自由店",
    "寵物公園–苗栗光復店",
    "寵物公園–小港漢民店",
    "寵物公園–新莊佳瑪店",
    "寵物公園–新莊復興店",
    "寵物公園–淡水中正店",
    "寵物公園–桃園青埔店",
    "寵物公園–台北忠五店",
    "寵物公園–彰化民族店",
    "貓狗隊長–嘉義仁愛店",
    "貓狗隊長–嘉義吳鳳店",
    "寵物公園–斗六民生店",
    "寵物公園–蘆洲集賢店",
    "寵物公園–安平店",
    "寵物公園–瑞豐店",
    "寵物公園–金龍店",
    "寵物公園–一心店",
    "寵物公園–青年店",
    "寵物公園–五甲店",
    "寵物公園–三多店",
    "寵物公園–鼎山店",
    "寵物公園–東門店",
    "寵物公園–西門店",
    "寵物公園–台南永康店",
    "寵物公園–逢甲店",
    "寵物公園–漢口店",
    "寵物公園–八德店",
    "寵物公園–南崁店",
    "寵物公園–中原店",
    "寵物公園–蘆洲店",
    "寵物公園–新中店",
    "寵物公園–淡北店",
    "寵物公園–汐康店",
    "寵物公園–汐福店",
    "寵物公園–汐止店",
    "寵物公園–新城店",
    "寵物公園–永貞店",
    "寵物公園–興南店",
    "寵物公園–雙和店",
    "寵物公園–頂溪店",
    "寵物公園–新陽店",
    "寵物公園–福德店",
    "寵物公園–新維店",
    "寵物公園–新雅店",
    "寵物公園–新海店",
    "寵物公園–文化店",
    "寵物公園–國光店",
    "寵物公園–石牌店",
    "寵物公園–北和店",
    "寵物公園–央北店",
    "寵物公園–內二店",
    "寵物公園–文德店",
    "寵物公園–景美店",
    "寵物公園–木新店",
    "寵物公園–台北新生店",
    "寵物公園–天母店",
    "寵物公園–文林店",
    "寵物公園–承四店",
    "寵物公園–林森店",
    "寵物公園–吉林店",
    "寵物公園–通化店",
    "寵物公園–新頭店",
    "寵物公園–竹雅店",
    "寵物公園–大興店",
    "寵物公園–板慶店",
    "寵物公園–健康店",
    "寵物公園-新月店",
    "凱朵寵物-三民店",
    "凱朵寵物-汐新店",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="POST WonderPet store names to /api/v1/property one by one."
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="API base URL. Default: http://localhost:8000",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=5.0,
        help="Delay between requests. Default: 5 seconds.",
    )
    parser.add_argument(
        "--brand",
        default=None,
        help="Optional brand prefix filter, e.g. 寵物公園 or 貓狗隊長.",
    )
    parser.add_argument(
        "--start-from",
        default=None,
        help="Start from the first matching store name.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit. 0 means no limit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned requests without sending them.",
    )
    return parser.parse_args()


def build_target_names(args: argparse.Namespace) -> list[str]:
    names = list(STORE_NAMES)
    if args.brand:
        names = [name for name in names if name.startswith(args.brand)]
    if args.start_from:
        for index, name in enumerate(names):
            if name == args.start_from:
                names = names[index:]
                break
        else:
            raise ValueError(f"start-from store not found: {args.start_from}")
    if args.limit > 0:
        names = names[: args.limit]
    return names


def post_create_property(base_url: str, store_name: str) -> tuple[int, str]:
    query = urllib.parse.urlencode({"name": store_name})
    url = f"{base_url.rstrip('/')}/api/v1/property?{query}"
    request = urllib.request.Request(url=url, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8", errors="ignore")
        return response.status, body


def main() -> int:
    args = parse_args()
    names = build_target_names(args)
    print(json.dumps({"count": len(names), "dry_run": args.dry_run}, ensure_ascii=False))

    for index, store_name in enumerate(names, start=1):
        if args.dry_run:
            print(f"[DRY-RUN] {index}/{len(names)} {store_name}")
            continue

        try:
            status, body = post_create_property(args.base_url, store_name)
            print(f"[{index}/{len(names)}] {status} {store_name} -> {body}")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            print(
                f"[{index}/{len(names)}] HTTP {exc.code} {store_name} -> {error_body}",
                file=sys.stderr,
            )
        except Exception as exc:
            print(
                f"[{index}/{len(names)}] ERROR {store_name} -> {exc}",
                file=sys.stderr,
            )

        if index < len(names):
            time.sleep(args.delay_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
