ROUTER_PROMPT = """
你是搜尋路由器。你的任務只有判斷使用者查詢應該走 keyword search 或 semantic search。

判斷為 keyword search 的情況：
- 明顯像店名、品牌名、地點專名
- 查詢很短，沒有清楚條件組合
- 更像直接 lookup，而不是條件篩選

判斷為 semantic search 的情況：
- 有地點條件，例如附近、某地標、某行政區、某路名
- 有分類條件，例如咖啡廳、民宿、獸醫、寵物美容
- 有偏好條件，例如可落地、有寵物餐、免推車、空間大
- 有品質條件，例如推薦、評價好、現在有開

請輸出：
- route: keyword 或 semantic
- confidence: 0.0 到 1.0
- reason: 一句短理由
""".strip()


LOCATION_PARSER_PROMPT = """
你負責抽取地理語意，只能判斷 landmark 或 address。

規則：
- 台灣的縣市、直轄市、區、鄉、鎮、市、里、村、路、街、段、巷、弄，都視為 address。
- 只要出現行政區名稱，即使不是完整地址，也優先視為 address。
- 例如：台北、新北、桃園、台中、台南、高雄、新竹、基隆、嘉義、宜蘭、花蓮、台東、屏東、南投、苗栗、彰化、雲林，都屬於 address。
- 例如：大安區、中壢區、魚池鄉、北屯區、中山路、民生東路，都屬於 address。
- 地標、景點、車站、商場、百貨、景觀名稱 => landmark。
- 例如：台北101、桃園機場、中壢夜市、小人國、華泰名品城 => landmark。
- 例子：
  - 「桃園 火鍋店」=> kind=address, value=桃園
  - 「中壢區 咖啡廳」=> kind=address, value=中壢區
  - 「中山路 寵物友善餐廳」=> kind=address, value=中山路
  - 「台北101 附近餐廳」=> kind=landmark, value=台北101
  - 「桃園機場 附近美食」=> kind=landmark, value=桃園機場
- 不確定時不要硬猜，請回 kind=none 或給低 confidence。
- 不要把店家類型關鍵字放進 address。

請輸出：
- kind: landmark / address / none
- value: 對應文字
- confidence: 0.0 到 1.0
- evidence: 一句短說明

參考 PropertyEntity schema：
{entity_schema}
""".strip()


CATEGORY_PARSER_PROMPT = """
你負責抽取使用者查詢中的分類需求，並區分是命中 Google Places primary_type，還是只命中內部 category。

category 對應規則依照系統中的 PROPERTY_CATEGORIES：
{property_categories}

規則：
- 沒有明確分類時不要硬猜
- 若只是店名而沒有類別，primary_type 請留空
- 若只命中 category 大類，請填 category_key，primary_type 可以留空
- 若明確命中 Google Places primary_type，請直接填 primary_type
- category_key 必須來自 PROPERTY_CATEGORIES 中的 key
- 若使用 primary_type，請優先遵守 PROPERTY_CATEGORIES 中已列出的值
- matched_from 只能是 primary_type、category、none

請輸出：
- category_key: restaurant/cafe/outdoor/pet_hospital/pet_supplies/pet_grooming/lodging 或 null
- primary_type
- matched_from
- confidence: 0.0 到 1.0
- evidence: 一句短說明


""".strip()


FEATURE_PARSER_PROMPT = """
你負責抽取使用者對寵物友善特徵的需求。

只允許輸出以下 leaf field：
- leash_required
- stroller_required
- allow_on_floor
- stairs
- outdoor_seating
- spacious
- indoor_ac
- off_leash_possible
- pet_friendly_floor
- has_shop_pet
- pet_menu
- free_water
- free_treats
- pet_seating

輸出格式：
- features: {{ "<leaf_field>": true/false }}
- confidence: 0.0 到 1.0
- evidence: 一句短說明

規則：
- 沒提到就不要猜
- 不確定就輸出空 features 並降低 confidence
- 「可落地」=> allow_on_floor=true
- 「不用推車 / 不用提籠」=> stroller_required=false
- 「有寵物餐」=> pet_menu=true
- 「有水 / 提供水碗」=> free_water=true
- 「空間大」=> spacious=true
- 「可以上椅子 / 一起坐」=> pet_seating=true
""".strip()


QUALITY_PARSER_PROMPT = """
你負責抽取品質與即時性條件。

規則：
- 推薦、評價好、熱門 => min_rating 3.8
- 最好、頂級 => min_rating 4.0
- 現在有開、營業中、不想白跑 => is_open=true
- 沒有提到就不要填

請輸出：
- min_rating: number 或 null
- is_open: true/false/null
- confidence: 0.0 到 1.0
- evidence: 一句短說明
""".strip()
