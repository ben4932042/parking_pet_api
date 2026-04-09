import logging
from typing import Iterable

import requests

from domain.entities.enrichment import PlaceCandidate, PlaceDetail, Review
from domain.entities.parking import NearbyParkingCandidate
from infrastructure.config import settings


logger = logging.getLogger(__name__)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/"
LEGACY_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
NEARBY_SEARCH_URL = "https://places.googleapis.com/v1/places:searchNearby"


def search_basic_information_by_name(name: str) -> PlaceCandidate:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google.place_api_key.get_secret_value(),
    }

    pro_mask = (
        "places.id,places.displayName,places.formattedAddress,places.location,"
        "places.types,places.businessStatus,places.primaryType,"
        "places.internationalPhoneNumber,places.websiteUri,places.userRatingCount,"
        "places.paymentOptions,places.parkingOptions,places.accessibilityOptions,"
        "places.takeout,places.delivery,places.dineIn"
    )

    payload = {
        "textQuery": name,
        "languageCode": "zh-TW",
        "maxResultCount": 1,
    }

    headers["X-Goog-FieldMask"] = pro_mask
    response = requests.post(SEARCH_URL, json=payload, headers=headers)

    if response.status_code != 200 or "places" not in response.json():
        print(f"Failed to search: {name}")
        print(f"Response: {response.text}")
        return None

    place = response.json()["places"][0]

    return PlaceCandidate(
        id=place.get("id"),
        origin_search_name=name,
        display_name=place.get("displayName", {}).get("text"),
        place_id=place.get("id"),
        latitude=place.get("location", {}).get("latitude"),
        longitude=place.get("location", {}).get("longitude"),
        address=place.get("formattedAddress"),
        types=place.get("types", []),
        primary_type=place.get("primaryType"),
        business_status=place.get("businessStatus"),
        phone_number=place.get("internationalPhoneNumber"),
        website=place.get("websiteUri"),
        user_rating_count=place.get("userRatingCount", 0),
        payment_methods=place.get("paymentOptions"),
        parking_options=place.get("parkingOptions"),
        accessibility_options=place.get("accessibilityOptions"),
        takeout=place.get("takeout"),
        delivery=place.get("delivery"),
        dine_in=place.get("dineIn"),
    )


def geocode_landmark_by_name(name: str) -> tuple[str, tuple[float, float] | None]:
    place = search_basic_information_by_name(name)
    if place is None:
        return name, None
    if place.longitude is None or place.latitude is None:
        return place.display_name or name, None
    return place.display_name or name, (place.longitude, place.latitude)


def get_basic_information_by_place_id(place_id: str) -> PlaceCandidate | None:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google.place_api_key.get_secret_value(),
        "X-Goog-FieldMask": (
            "id,displayName,formattedAddress,location,types,businessStatus,"
            "primaryType,internationalPhoneNumber,websiteUri,userRatingCount,"
            "paymentOptions,parkingOptions,accessibilityOptions,takeout,delivery,dineIn"
        ),
    }

    response = requests.get(
        f"{DETAILS_URL}{place_id}",
        headers=headers,
        params={"languageCode": "zh-TW"},
        timeout=10,
    )
    response.raise_for_status()
    place = response.json()

    return PlaceCandidate(
        id=place.get("id"),
        origin_search_name=place.get("displayName", {}).get("text") or place_id,
        display_name=place.get("displayName", {}).get("text"),
        place_id=place.get("id"),
        latitude=place.get("location", {}).get("latitude"),
        longitude=place.get("location", {}).get("longitude"),
        address=place.get("formattedAddress"),
        types=place.get("types", []),
        primary_type=place.get("primaryType"),
        business_status=place.get("businessStatus"),
        phone_number=place.get("internationalPhoneNumber"),
        website=place.get("websiteUri"),
        user_rating_count=place.get("userRatingCount", 0),
        payment_methods=place.get("paymentOptions"),
        parking_options=place.get("parkingOptions"),
        accessibility_options=place.get("accessibilityOptions"),
        takeout=place.get("takeout"),
        delivery=place.get("delivery"),
        dine_in=place.get("dineIn"),
    )


def _normalize_review_author(author: str | None) -> str | None:
    if author is None:
        return None
    normalized = author.strip()
    return normalized or None


def _normalize_review_text(text: str | None) -> str | None:
    if text is None:
        return None
    normalized = text.strip()
    return normalized or None


def _merge_reviews_by_author(*review_groups: Iterable[Review]) -> list[Review]:
    merged_reviews: list[Review] = []
    author_to_index: dict[str, int] = {}

    for reviews in review_groups:
        for review in reviews:
            author = _normalize_review_author(review.author)
            text = _normalize_review_text(review.text)
            if author is None or text is None:
                continue

            normalized_review = review.model_copy(update={"author": author, "text": text})
            existing_index = author_to_index.get(author)
            if existing_index is None:
                author_to_index[author] = len(merged_reviews)
                merged_reviews.append(normalized_review)
            else:
                merged_reviews[existing_index] = normalized_review

    return merged_reviews


def _fetch_place_details_new_api(place_id: str) -> dict:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google.place_api_key.get_secret_value(),
        "X-Goog-FieldMask": (
            "rating,reviews,userRatingCount,priceLevel,regularOpeningHours,"
            "allowsDogs,outdoorSeating,reservable,goodForChildren,goodForGroups,"
            "servesBeer,servesWine"
        ),
    }

    response = requests.get(
        f"{DETAILS_URL}{place_id}",
        headers=headers,
        params={"languageCode": "zh-TW"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _fetch_place_details_legacy_reviews(place_id: str) -> dict:
    response = requests.get(
        LEGACY_DETAILS_URL,
        params={
            "place_id": place_id,
            "key": settings.google.place_api_key.get_secret_value(),
            "language": "zh-TW",
            "reviews_sort": "newest",
            "reviews_no_translations": "true",
            "fields": "review,rating,user_ratings_total",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _parse_new_api_reviews(details: dict) -> list[Review]:
    return [
        Review(
            author=r.get("authorAttribution", {}).get("displayName"),
            rating=r.get("rating"),
            text=r.get("text", {}).get("text"),
            time=r.get("relativePublishTimeDescription"),
        )
        for r in details.get("reviews", [])
    ]


def _parse_legacy_reviews(details: dict) -> list[Review]:
    result = details.get("result", {})
    return [
        Review(
            author=r.get("author_name"),
            rating=r.get("rating"),
            text=r.get("text"),
            time=r.get("relative_time_description"),
        )
        for r in result.get("reviews", [])
    ]


def get_place_details(basic_info: PlaceCandidate) -> PlaceDetail | None:
    try:
        details = _fetch_place_details_new_api(basic_info.place_id)
        legacy_details = _fetch_place_details_legacy_reviews(basic_info.place_id)
        new_reviews = _parse_new_api_reviews(details)
        legacy_reviews = _parse_legacy_reviews(legacy_details)
        formatted_reviews = _merge_reviews_by_author(
            new_reviews,
            legacy_reviews,
        )
        logger.info(
            "Fetched place details reviews from Google Places",
            extra={
                "place_id": basic_info.place_id,
                "display_name": basic_info.display_name,
                "new_api_review_count": len(new_reviews),
                "legacy_review_count": len(legacy_reviews),
                "merged_review_count": len(formatted_reviews),
                "new_api_user_rating_count": details.get("userRatingCount"),
                "legacy_status": legacy_details.get("status"),
            },
        )

        return PlaceDetail(
            id=basic_info.place_id,
            rating=details.get("rating"),
            user_rating_count=details.get("userRatingCount"),
            price_level=details.get("priceLevel"),
            regular_opening_hours=details.get("regularOpeningHours", {}).get("periods"),
            allows_dogs=details.get("allowsDogs"),
            outdoor_seating=details.get("outdoorSeating"),
            reservable=details.get("reservable"),
            good_for_children=details.get("goodForChildren"),
            good_for_groups=details.get("goodForGroups"),
            serves_beer=details.get("servesBeer"),
            serves_wine=details.get("servesWine"),
            reviews=formatted_reviews,
        )

    except Exception as e:
        logger.exception(f"Failed to get place details {str(e)}", exc_info=True)


def search_nearby_parking(
    lat: float,
    lng: float,
    *,
    radius: float = 2000.0,
    max_result_count: int = 20,
) -> list[NearbyParkingCandidate]:
    logger.info(
        "Searching nearby parking from Google Places",
        extra={
            "lat": lat,
            "lng": lng,
            "radius": radius,
            "max_result_count": max_result_count,
        },
    )
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google.place_api_key.get_secret_value(),
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.primaryType,places.types"
        ),
    }

    payload = {
        "includedTypes": ["parking"],
        "maxResultCount": max_result_count,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lng,
                },
                "radius": radius,
            }
        },
        "languageCode": "zh-TW",
    }

    response = requests.post(
        NEARBY_SEARCH_URL,
        json=payload,
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()

    places = response.json().get("places", [])
    logger.info(
        "Google Places nearby parking search completed",
        extra={
            "lat": lat,
            "lng": lng,
            "radius": radius,
            "returned_places_count": len(places),
        },
    )
    candidates: list[NearbyParkingCandidate] = []
    skipped_count = 0

    for place in places:
        place_id = place.get("id")
        display_name = place.get("displayName", {}).get("text")
        location = place.get("location") or {}
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if not place_id or not display_name or latitude is None or longitude is None:
            skipped_count += 1
            continue

        candidates.append(
            NearbyParkingCandidate(
                place_id=place_id,
                name=display_name,
                latitude=latitude,
                longitude=longitude,
                address=place.get("formattedAddress"),
                primary_type=place.get("primaryType"),
                types=place.get("types", []),
            )
        )

    logger.info(
        "Normalized nearby parking candidates",
        extra={
            "lat": lat,
            "lng": lng,
            "candidate_count": len(candidates),
            "skipped_count": skipped_count,
        },
    )
    return candidates
