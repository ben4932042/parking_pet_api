import requests
import logging

from infrastructure.config import settings



logger = logging.getLogger(__name__)


SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
DETAILS_URL = "https://places.googleapis.com/v1/places/"


def get_new_property_data(property_name: str):
    """"""
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": settings.google.place_api_key.get_secret_value()}

    pro_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.types,places.businessStatus"
    search_payload = {
        "textQuery": property_name,
        "languageCode": "zh-TW",
        "maxResultCount": 1,
    }

    try:
        search_headers = headers.copy()
        search_headers["X-Goog-FieldMask"] = pro_mask
        s_res = requests.post(SEARCH_URL, json=search_payload, headers=search_headers)

        if s_res.status_code != 200 or "places" not in s_res.json():
            logging.exception(f"Failed to search for property: {property_name}")

        place = s_res.json()["places"][0]
        place_id = place["id"]

        ent_mask = "displayName,rating,reviews,userRatingCount,priceLevel"
        details_headers = headers.copy()
        details_headers["X-Goog-FieldMask"] = ent_mask

        d_res = requests.get(
            f"{DETAILS_URL}{place_id}",
            headers=details_headers,
            params={"languageCode": "zh-TW"},
        )

        if d_res.status_code == 200:
            details = d_res.json()
            reviews = details.get("reviews", [])

            formatted_reviews = [
                {
                    "author": r.get("authorAttribution", {}).get("displayName"),
                    "rating": r.get("rating"),
                    "text": r.get("text", {}).get("text"),
                    "time": r.get("relativePublishTimeDescription"),
                }
                for r in reviews
            ]


            result_dict = {
                "origin_search_name": property_name,
                "display_name": details.get("displayName", {}).get("text"),
                "place_id": place_id,
                "latitude": place.get("location", {}).get("latitude"),
                "longitude": place.get("location", {}).get("longitude"),
                "location": {
                    "type": "Point",
                    "coordinates": [place.get("location", {}).get("longitude"), place.get("location", {}).get("latitude")]
                },
                "address": place.get("formattedAddress"),
                "rating": details.get("rating"),
                "user_rating_count": details.get("userRatingCount"),
                "price_level": details.get("priceLevel"),
                "types": ', '.join(place.get("types", [])),
                "reviews": '\n'.join([f"{r['author']} ({r['rating']}): {r['text']} [{r['time']}]" for r in formatted_reviews]),
            }
            return result_dict

    except Exception as e:
        return {"error": str(e), "status": "EXCEPTION"}


if __name__ == "__main__":
    new_shop = get_new_property_data("春花炭火串燒")
    print(new_shop)


