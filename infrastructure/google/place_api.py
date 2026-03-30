import requests
import logging

from domain.entities.enrichment import PlaceCandidate, PlaceDetail, Review
from infrastructure.config import settings


logger = logging.getLogger(__name__)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/"


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


def get_place_details(basic_info: PlaceCandidate) -> PlaceDetail | None:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google.place_api_key.get_secret_value(),
    }

    pro_mask = (
        "rating,reviews,userRatingCount,priceLevel,regularOpeningHours,"
        "allowsDogs,outdoorSeating,reservable,goodForChildren,goodForGroups,"
        "servesBeer,servesWine"
    )

    headers["X-Goog-FieldMask"] = pro_mask

    try:
        response = requests.get(
            f"{DETAILS_URL}{basic_info.place_id}",
            headers=headers,
            params={"languageCode": "zh-TW"},
        )
        response.raise_for_status()

        details = response.json()

        formatted_reviews = [
            Review(
                author=r.get("authorAttribution", {}).get("displayName"),
                rating=r.get("rating"),
                text=r.get("text", {}).get("text"),
                time=r.get("relativePublishTimeDescription"),
            )
            for r in details.get("reviews", [])
        ]

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
