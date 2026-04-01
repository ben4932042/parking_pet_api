import re

from domain.entities.property import PropertyEntity

CHINESE_BRANCH_SUFFIX_PATTERN = re.compile(
    r"\s*(台北101店|[^\s]+(?:旗艦店|概念店|門市|分店|店|館))\s*$"
)
SEPARATOR_SUFFIX_PATTERN = re.compile(r"\s*[-|｜:：]\s*.+$")
TRAILHEAD_SUFFIX_PATTERN = re.compile(r"(步道)(?:入口|登山口)\s*$")
COMMON_ENGLISH_LOCATION_WORDS = {
    "taipei",
    "taichung",
    "tainan",
    "kaohsiung",
    "taoyuan",
    "hsinchu",
    "keelung",
    "chiayi",
    "yilan",
    "pingtung",
    "banqiao",
    "xinyi",
    "zhongshan",
    "daan",
    "east district",
    "west district",
    "north district",
    "south district",
    "central district",
}


def build_property_alias_fields(property_entity: PropertyEntity) -> dict[str, object]:
    generated_aliases = _build_generated_aliases(property_entity.name)
    aliases = _merge_aliases(generated_aliases, property_entity.manual_aliases)
    return {
        "aliases": aliases,
    }


def _build_generated_aliases(name: str) -> list[str]:
    normalized_name = _normalize_space(name)
    if not normalized_name:
        return []

    aliases: list[str] = []
    seen = {normalized_name.casefold()}

    for candidate in (
        _strip_suffix_after_at(normalized_name),
        _strip_parenthetical_suffix(normalized_name),
        _strip_separator_suffix(normalized_name),
        _strip_branch_suffix(normalized_name),
        _strip_english_location_suffix(normalized_name),
        _strip_trailhead_suffix(normalized_name),
        _extract_park_alias(normalized_name),
    ):
        cleaned = _normalize_space(candidate)
        if not cleaned:
            continue
        lowered = cleaned.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        aliases.append(cleaned)

    return aliases


def _merge_aliases(generated_aliases: list[str], manual_aliases: list[str]) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()

    for candidate in [*generated_aliases, *manual_aliases]:
        cleaned = _normalize_space(candidate)
        if not cleaned:
            continue
        lowered = cleaned.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        aliases.append(cleaned)

    return aliases
def _normalize_space(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _strip_suffix_after_at(name: str) -> str:
    if "@" not in name:
        return ""
    return name.split("@", 1)[0].strip()


def _strip_parenthetical_suffix(name: str) -> str:
    return re.sub(r"\s*[\(\（][^\)\）]*[\)\）]\s*$", "", name).strip()


def _strip_separator_suffix(name: str) -> str:
    stripped = SEPARATOR_SUFFIX_PATTERN.sub("", name).strip()
    return stripped.rstrip("-|｜:：").strip()


def _strip_branch_suffix(name: str) -> str:
    stripped = CHINESE_BRANCH_SUFFIX_PATTERN.sub("", name).strip()
    return stripped.rstrip("-|｜:：").strip()


def _strip_english_location_suffix(name: str) -> str:
    normalized_name = _normalize_space(name)
    for suffix in sorted(COMMON_ENGLISH_LOCATION_WORDS, key=len, reverse=True):
        token = f" {suffix}"
        if normalized_name.casefold().endswith(token):
            return normalized_name[: -len(token)].strip()
    return ""


def _strip_trailhead_suffix(name: str) -> str:
    return TRAILHEAD_SUFFIX_PATTERN.sub(r"\1", name).strip()


def _extract_park_alias(name: str) -> str:
    match = re.search(r"(公[^\\s]*公園)$", name)
    if not match:
        return ""
    return match.group(1).strip()
