from domain.entities.property_category import PropertyCategoryKey


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
    "台北大巨蛋",
    "台北小巨蛋",
]

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
    "is_open": (
        "現在有開",
        "營業中",
        "現在營業",
        "開著",
        "不想白跑",
        "有開",
        "有開的",
        "有營業",
        "有營業的",
    ),
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

SEMANTIC_SEARCH_INTENT_PHRASES = (
    "想",
    "找",
    "推薦",
    "附近",
    "哪裡",
    "有沒有",
    "可以",
)

HYBRID_EXACT_QUERIES = {
    "寵物公園",
}
