import re

from domain.entities.property_category import PropertyCategoryKey, PROPERTY_CATEGORIES
from domain.entities.search import (
    CategoryIntent,
    DistanceIntent,
    PetFeatureIntent,
    QualityIntent,
)


FEATURE_FIELD_MAP = {
    "leash_required": "effective_pet_features.rules.leash_required",
    "stroller_required": "effective_pet_features.rules.stroller_required",
    "allow_on_floor": "effective_pet_features.rules.allow_on_floor",
    "stairs": "effective_pet_features.environment.stairs",
    "outdoor_seating": "effective_pet_features.environment.outdoor_seating",
    "spacious": "effective_pet_features.environment.spacious",
    "indoor_ac": "effective_pet_features.environment.indoor_ac",
    "off_leash_possible": "effective_pet_features.environment.off_leash_possible",
    "pet_friendly_floor": "effective_pet_features.environment.pet_friendly_floor",
    "has_shop_pet": "effective_pet_features.environment.has_shop_pet",
    "pet_menu": "effective_pet_features.services.pet_menu",
    "free_water": "effective_pet_features.services.free_water",
    "free_treats": "effective_pet_features.services.free_treats",
    "pet_seating": "effective_pet_features.services.pet_seating",
}

TAIWAN_ADDRESS_KEYWORDS = [
    "台北",
    "臺北",
    "新北",
    "桃園",
    "台中",
    "臺中",
    "台南",
    "臺南",
    "高雄",
    "基隆",
    "新竹",
    "苗栗",
    "彰化",
    "南投",
    "雲林",
    "嘉義",
    "屏東",
    "宜蘭",
    "花蓮",
    "台東",
    "臺東",
    "澎湖",
    "金門",
    "連江",
]
ADDRESS_SUFFIX_PATTERN = re.compile(
    r"(?P<value>[^\s,，。]{1,12}(?:縣|市|區|鄉|鎮|村|里|路|街|大道|段|巷|弄))"
)

RULE_BASED_PRIMARY_TYPE_KEYWORDS = [
    ("公園", "park"),
    ("火鍋", "hot_pot_restaurant"),
    ("燒肉", "yakiniku_restaurant"),
    ("烤肉", "yakiniku_restaurant"),
    ("拉麵", "ramen_restaurant"),
    ("早午餐", "brunch_restaurant"),
    ("餐酒館", "bistro"),
    ("獸醫", "veterinary_care"),
    ("看醫生", "veterinary_care"),
    ("寵物美容", "pet_care"),
    ("洗澡", "pet_care"),
    ("剪毛", "pet_care"),
    ("美容", "pet_care"),
    ("寵物用品", "pet_store"),
]

RULE_BASED_CATEGORY_KEYWORDS = [
    ("咖啡廳", PropertyCategoryKey.CAFE),
    ("咖啡店", PropertyCategoryKey.CAFE),
    ("下午茶", PropertyCategoryKey.CAFE),
    ("點心", PropertyCategoryKey.CAFE),
    ("甜點", PropertyCategoryKey.CAFE),
    ("餐廳", PropertyCategoryKey.RESTAURANT),
    ("美食", PropertyCategoryKey.RESTAURANT),
    ("戶外", PropertyCategoryKey.OUTDOOR),
    ("住宿", PropertyCategoryKey.LODGING),
    ("民宿", PropertyCategoryKey.LODGING),
    ("旅館", PropertyCategoryKey.LODGING),
]

RULE_BASED_LANDMARK_KEYWORDS = [
    "青埔",
    "台北101",
    "日月潭",
    "阿里山",
    "太魯閣",
    "清境農場",
    "陽明山",
    "九份",
    "十分",
    "野柳",
    "墾丁",
]

RULE_BASED_LANDMARK_SUFFIXES = (
    "夜市",
    "老街",
    "車站",
    "機場",
    "漁港",
    "碼頭",
    "百貨",
    "名品城",
    "美術館",
    "博物館",
    "動物園",
    "植物園",
    "風景區",
    "國家公園",
    "森林遊樂區",
    "遊樂區",
    "遊樂園",
)

FEATURE_HINT_KEYWORDS = {
    "leash_required": ("牽繩",),
    "stroller_required": ("推車", "提籠"),
    "allow_on_floor": ("可落地", "落地", "空出雙手"),
    "stairs": ("樓梯",),
    "outdoor_seating": ("戶外", "露天", "戶外座位"),
    "spacious": ("空間大", "寬敞"),
    "indoor_ac": ("冷氣", "空調", "避暑"),
    "off_leash_possible": ("放繩", "奔跑"),
    "pet_friendly_floor": ("止滑", "地墊"),
    "has_shop_pet": ("有店狗", "有店貓", "店裡有狗"),
    "pet_menu": ("寵物餐",),
    "free_water": ("水碗", "飲水", "有水"),
    "free_treats": ("零食",),
    "pet_seating": ("上椅", "一起坐", "座位"),
}

NEGATIVE_FEATURE_HINT_KEYWORDS = {
    "stroller_required": (
        "不需要推車",
        "不用推車",
        "免推車",
        "不需要提籠",
        "不用提籠",
        "免提籠",
    ),
    "allow_on_floor": ("不可落地", "不能落地"),
    "has_shop_pet": ("沒有店狗",),
}

QUALITY_HINT_KEYWORDS = {
    "min_rating": ("推薦", "評價", "熱門", "最好", "頂級"),
    "is_open": ("現在有開", "營業中", "現在營業", "開著", "不想白跑", "有開", "有開的"),
}

TRANSPORT_SPEED_KMH = {
    "driving": 50,
    "bicycling": 15,
    "walking": 5,
}
TRANSPORT_DISTANCE_DISCOUNT = {
    "driving": 0.9,
    "bicycling": 0.9,
    "walking": 0.9,
}
TRANSPORT_LABELS = {
    "driving": "車程",
    "bicycling": "騎車",
    "walking": "步行",
}
TRANSPORT_KEYWORDS = {
    "walking": ("步行", "走路", "徒步"),
    "bicycling": ("騎車", "單車", "自行車", "腳踏車", "騎腳踏車"),
    "driving": ("開車", "車程"),
}
TRANSPORT_PHRASES = {
    keyword for keywords in TRANSPORT_KEYWORDS.values() for keyword in keywords
}
TRAVEL_TIME_PATTERN = re.compile(
    r"(?:距離\s*)?(?:(?P<prefix_mode>步行|走路|徒步|騎車|單車|自行車|腳踏車|騎腳踏車|開車|車程)\s*)?(?P<minutes>[零一二兩三四五六七八九十百\d]{1,4})\s*分鐘(?:\s*(?P<suffix_mode>步行|走路|徒步|騎車|單車|自行車|腳踏車|騎腳踏車|開車|車程|內))?"
)

CHINESE_NUMBER_MAP = {
    "零": 0,
    "一": 1,
    "二": 2,
    "兩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

NON_SEARCH_EXACT_QUERIES = {
    "你好",
    "哈囉",
    "嗨",
    "謝謝",
    "感謝",
    "你是誰",
    "你會什麼",
    "你可以做什麼",
}

NON_SEARCH_PHRASES = (
    "幫我分析",
    "幫我看",
    "你看一下",
    "這是什麼",
    "怎麼用",
    "怎麼做",
)

PROMPT_INJECTION_PATTERNS = (
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "developer message",
    "reveal your prompt",
    "忽略之前",
    "忽略前面",
    "忽略以上",
    "忘掉之前",
    "系統提示",
    "系統 prompt",
    "開發者訊息",
    "developer prompt",
    "你現在是",
    "請扮演",
    "roleplay as",
    "act as",
)

NEGATION_PREFIXES = ("不", "不是", "非", "免", "不要", "不用", "無需")


def normalize_text_for_match(value: str) -> str:
    return re.sub(r"\s+", "", value).strip()


def is_basic_prompt_injection(query: str) -> bool:
    normalized_query = query.lower()
    return any(pattern in normalized_query for pattern in PROMPT_INJECTION_PATTERNS)


def is_negated_keyword(query: str, keyword: str) -> bool:
    index = query.find(keyword)
    if index == -1:
        return False

    prefix = query[:index]
    return any(prefix.endswith(negation) for negation in NEGATION_PREFIXES)


def extract_landmark_by_rule(query: str) -> str | None:
    normalized_query = normalize_text_for_match(query)
    if not normalized_query:
        return None

    for keyword in sorted(RULE_BASED_LANDMARK_KEYWORDS, key=len, reverse=True):
        normalized_keyword = normalize_text_for_match(keyword)
        keyword_index = normalized_query.find(normalized_keyword)
        if keyword_index != -1:
            next_index = keyword_index + len(normalized_keyword)
            if next_index < len(normalized_query) and normalized_query[next_index] in {
                "鐘",
                "钟",
            }:
                continue
            return keyword

    if any(
        normalized_query.endswith(suffix) for suffix in RULE_BASED_LANDMARK_SUFFIXES
    ):
        return query.strip()

    if (
        normalized_query[-1:] in {"潭", "湖", "山", "溪", "島"}
        and len(normalized_query) <= 6
    ):
        return query.strip()

    return None


def extract_address_by_rule(query: str) -> str | None:
    rule_based_landmark = extract_landmark_by_rule(query)

    for keyword in sorted(TAIWAN_ADDRESS_KEYWORDS, key=len, reverse=True):
        if keyword in query:
            if (
                rule_based_landmark
                and keyword in rule_based_landmark
                and len(keyword) < len(rule_based_landmark)
            ):
                continue
            return keyword

    match = ADDRESS_SUFFIX_PATTERN.search(query)
    if match:
        value = match.group("value")
        if value in TRANSPORT_PHRASES:
            return None
        return value

    return None


def extract_category_by_rule(query: str) -> CategoryIntent | None:
    for keyword, primary_type in RULE_BASED_PRIMARY_TYPE_KEYWORDS:
        if is_negated_keyword(query, keyword):
            continue
        if keyword in query:
            return CategoryIntent(
                primary_type=primary_type,
                matched_from="primary_type",
                confidence=0.95,
                evidence=f"matched primary type keyword by rule: {keyword}",
            )

    for keyword, category_key in RULE_BASED_CATEGORY_KEYWORDS:
        if is_negated_keyword(query, keyword):
            continue
        if keyword in query:
            return CategoryIntent(
                category_key=category_key,
                matched_from="category",
                confidence=0.95,
                evidence=f"matched category keyword by rule: {keyword}",
            )

    return None


def is_pure_landmark_query(query: str) -> bool:
    landmark = extract_landmark_by_rule(query)
    if not landmark:
        return False

    normalized_query = normalize_text_for_match(query)
    normalized_landmark = normalize_text_for_match(landmark)
    if normalized_query != normalized_landmark:
        return False

    return extract_category_by_rule(query) is None


def has_feature_hints(query: str) -> bool:
    return any(
        keyword in query
        for keywords in FEATURE_HINT_KEYWORDS.values()
        for keyword in keywords
    ) or any(
        keyword in query
        for keywords in NEGATIVE_FEATURE_HINT_KEYWORDS.values()
        for keyword in keywords
    )


def extract_feature_by_rule(query: str) -> PetFeatureIntent | None:
    if not has_feature_hints(query):
        return None

    features: dict[str, bool] = {}
    matched_keywords: list[str] = []

    for feature_name, keywords in NEGATIVE_FEATURE_HINT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query:
                features[feature_name] = False
                matched_keywords.append(keyword)
                break

    for feature_name, keywords in FEATURE_HINT_KEYWORDS.items():
        if feature_name in features:
            continue
        for keyword in keywords:
            if keyword in query:
                features[feature_name] = True
                matched_keywords.append(keyword)
                break

    if not features:
        return None

    return PetFeatureIntent(
        features=features,
        confidence=0.98,
        evidence=f"matched pet feature keywords by rule: {', '.join(matched_keywords)}",
    )


def has_quality_hints(query: str) -> bool:
    return any(
        keyword in query
        for keywords in QUALITY_HINT_KEYWORDS.values()
        for keyword in keywords
    )


def extract_quality_by_rule(query: str) -> QualityIntent | None:
    if not has_quality_hints(query):
        return None

    min_rating = None
    is_open = None
    matched_keywords: list[str] = []

    if any(keyword in query for keyword in ("最好", "頂級")):
        min_rating = 4.0
        matched_keywords.extend(
            [keyword for keyword in ("最好", "頂級") if keyword in query]
        )
    elif any(keyword in query for keyword in ("推薦", "評價", "熱門")):
        min_rating = 3.8
        matched_keywords.extend(
            [keyword for keyword in ("推薦", "評價", "熱門") if keyword in query]
        )

    if any(keyword in query for keyword in QUALITY_HINT_KEYWORDS["is_open"]):
        is_open = True
        matched_keywords.extend(
            [
                keyword
                for keyword in QUALITY_HINT_KEYWORDS["is_open"]
                if keyword in query
            ]
        )

    return QualityIntent(
        min_rating=min_rating,
        is_open=is_open,
        confidence=0.98,
        evidence=f"matched quality keywords by rule: {', '.join(dict.fromkeys(matched_keywords))}",
    )


def detect_transport_mode(query: str, matched_mode: str | None = None) -> str:
    if matched_mode:
        for mode, keywords in TRANSPORT_KEYWORDS.items():
            if matched_mode in keywords:
                return mode

    for mode, keywords in TRANSPORT_KEYWORDS.items():
        if any(keyword in query for keyword in keywords):
            return mode

    return "driving"


def parse_travel_minutes(raw_value: str) -> int | None:
    raw_value = raw_value.strip()
    if raw_value.isdigit():
        return int(raw_value)

    if not raw_value:
        return None

    if raw_value == "十":
        return 10

    if "百" in raw_value:
        parts = raw_value.split("百", 1)
        hundreds = CHINESE_NUMBER_MAP.get(parts[0], 1) if parts[0] else 1
        remainder = parse_travel_minutes(parts[1]) or 0
        return hundreds * 100 + remainder

    if "十" in raw_value:
        parts = raw_value.split("十", 1)
        tens = CHINESE_NUMBER_MAP.get(parts[0], 1) if parts[0] else 1
        ones = CHINESE_NUMBER_MAP.get(parts[1], 0) if parts[1] else 0
        return tens * 10 + ones

    if len(raw_value) == 1:
        return CHINESE_NUMBER_MAP.get(raw_value)

    return None


def travel_minutes_to_radius_meters(minutes: int, transport_mode: str) -> int:
    distance_km = (
        TRANSPORT_SPEED_KMH[transport_mode]
        * (minutes / 60)
        * TRANSPORT_DISTANCE_DISCOUNT[transport_mode]
    )
    return round(distance_km * 1000)


def extract_distance_by_rule(query: str) -> DistanceIntent | None:
    match = TRAVEL_TIME_PATTERN.search(query)
    if not match:
        return None

    minutes = parse_travel_minutes(match.group("minutes"))
    if minutes is None or minutes <= 0:
        return None

    transport_mode = detect_transport_mode(
        query,
        matched_mode=match.group("prefix_mode") or match.group("suffix_mode"),
    )
    speed_kmh = TRANSPORT_SPEED_KMH[transport_mode]
    discount = TRANSPORT_DISTANCE_DISCOUNT[transport_mode]

    return DistanceIntent(
        transport_mode=transport_mode,
        travel_time_limit_min=minutes,
        search_radius_meters=travel_minutes_to_radius_meters(minutes, transport_mode),
        confidence=0.95,
        evidence=(
            "converted travel time to radius by rule "
            f"({transport_mode} {speed_kmh}km/h * {minutes}min * {discount})"
        ),
    )


def should_use_current_location_context(query: str) -> bool:
    if not TRAVEL_TIME_PATTERN.search(query):
        return False

    if extract_address_by_rule(query):
        return False

    if extract_landmark_by_rule(query):
        return False

    return True


def is_obviously_non_search_query(query: str) -> bool:
    normalized_query = normalize_text_for_match(query)
    if not normalized_query:
        return True

    if is_basic_prompt_injection(query):
        return False

    if normalized_query in {
        normalize_text_for_match(item) for item in NON_SEARCH_EXACT_QUERIES
    }:
        return True

    if any(phrase in query for phrase in NON_SEARCH_PHRASES):
        return True

    if extract_address_by_rule(query):
        return False

    if extract_landmark_by_rule(query):
        return False

    if extract_category_by_rule(query):
        return False

    if extract_feature_by_rule(query) or extract_quality_by_rule(query):
        return False

    if any(keyword in query for keyword in ("找", "搜尋", "附近")):
        return False

    if query.endswith(("嗎", "呢", "？", "?")):
        return True

    return False


def should_run_typo_normalizer(query: str) -> bool:
    normalized_query = normalize_text_for_match(query)
    if not normalized_query or len(normalized_query) < 2:
        return False

    if is_basic_prompt_injection(query):
        return False

    if is_obviously_non_search_query(query):
        return False

    if extract_landmark_by_rule(query):
        return False

    if extract_category_by_rule(query):
        return False

    if extract_feature_by_rule(query) or extract_quality_by_rule(query):
        return False

    rule_based_address = extract_address_by_rule(query)
    if rule_based_address:
        remaining_query = query.replace(rule_based_address, "").strip()
        return bool(remaining_query)

    return False


def normalize_category_intent(query: str, intent: CategoryIntent) -> CategoryIntent:
    if intent.primary_type and "," in intent.primary_type:
        rule_based = extract_category_by_rule(query)
        if rule_based:
            return rule_based

        raw_values = [
            item.strip() for item in intent.primary_type.split(",") if item.strip()
        ]
        unique_values = list(dict.fromkeys(raw_values))
        for category in PROPERTY_CATEGORIES:
            category_set = set(category.primary_types)
            if set(unique_values).issubset(category_set):
                return CategoryIntent(
                    category_key=category.key,
                    matched_from="category",
                    confidence=intent.confidence,
                    evidence="normalized comma-separated primary_type output into category",
                )
        if unique_values:
            return CategoryIntent(
                primary_type=unique_values[0],
                matched_from="primary_type",
                confidence=intent.confidence,
                evidence="normalized comma-separated primary_type output into first candidate",
            )

    return intent
