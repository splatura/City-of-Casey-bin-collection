import requests
import datetime

def get_casey_waste_services(address):
    try:
        # Step 1: Geocode address with multiple attempts
        geocode_url = "https://nominatim.openstreetmap.org/search"

        # Try original address first
        geo_params = {"format": "json", "q": address, "limit": 5}
        geo_resp = requests.get(
            geocode_url,
            params=geo_params,
            headers={'User-Agent': 'CaseyBinLookup/1.0'},
            timeout=10
        )
        geo_resp.raise_for_status()
        results = geo_resp.json()

        # If no results, try with more general address (suburb only)
        if not results:
            if "," in address:
                suburb_part = address.split(",")[1].strip() + ", Victoria, Australia"
                geo_params["q"] = suburb_part
                geo_resp = requests.get(
                    geocode_url,
                    params=geo_params,
                    headers={'User-Agent': 'CaseyBinLookup/1.0'},
                    timeout=10
                )
                geo_resp.raise_for_status()
                results = geo_resp.json()

        if not results:
            return {"error": "Address not found. Please check the address and try again."}

        lat, lon = results[0]["lat"], results[0]["lon"]
        # Extract postcode from geocoding result's display_name
        # Format: "2, Patrick Northeast Drive, Narre Warren, Melbourne, City of Casey, Victoria, 3805, Australia"
        display_name = results[0].get("display_name", "")
        geocoded_postcode = "Unknown"
        if display_name:
            # Split by comma and look for 4-digit Australian postcode
            parts = [p.strip() for p in display_name.split(",")]
            for part in parts:
                if part.isdigit() and len(part) == 4:
                    geocoded_postcode = part
                    break

        # Step 2: Query City of Casey Waste Collection API
        # Use geofilter.polygon to find the area that contains this exact point
        waste_api = "https://data.casey.vic.gov.au/api/explore/v2.1/catalog/datasets/waste-collection-area/records"

        # Try to find polygon containing the point
        waste_params = {"where": f"within_distance(geo_shape, geom'POINT({lon} {lat})', 1m)", "limit": 1}
        waste_resp = requests.get(waste_api, params=waste_params, timeout=10)
        waste_resp.raise_for_status()
        waste_data = waste_resp.json()

        # If no results with within_distance, fall back to distance search
        if not waste_data.get("results"):
            waste_params = {"geofilter.distance": f"{lat},{lon},1000", "limit": 1}
            waste_resp = requests.get(waste_api, params=waste_params, timeout=10)
            waste_resp.raise_for_status()
            waste_data = waste_resp.json()

        if not waste_data.get("results"):
            return {"error": "No waste collection data found for this location. This address may not be in the City of Casey area."}

        record = waste_data["results"][0]

        # Parse the collection field (format: "Monday_Week_2")
        collection_str = record.get("collection", "Unknown")
        if collection_str != "Unknown" and "_" in collection_str:
            parts = collection_str.split("_")
            collection_day = parts[0]
            collection_week = parts[2] if len(parts) > 2 else "Unknown"  # "Week_1" -> "1"
        else:
            collection_day = collection_str
            collection_week = "Unknown"

        # Use postcode from geocoding result (more accurate for the actual address)
        postcode = geocoded_postcode

        # Step 3: Calculate current week (1 or 2)
        # City of Casey alternates fortnightly
        # Using 20 Oct 2025 (Monday) as reference for Week 2 pattern
        # (validated: Thursday 23 Oct 2025 = Week 2 areas get recycling collection)
        ref_date = datetime.date(2025, 10, 20)
        current_date = datetime.date.today()
        weeks_since_ref = (current_date - ref_date).days // 7
        # Week 2 areas collect on even weeks (0, 2, 4...), Week 1 areas on odd weeks
        current_week = 2 if weeks_since_ref % 2 == 0 else 1

        # Calculate the night before collection day
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        night_before = "Unknown"
        if collection_day in days_of_week:
            day_index = days_of_week.index(collection_day)
            night_before_index = (day_index - 1) % 7
            night_before = days_of_week[night_before_index]

        # Determine which bins go out based on the area's assigned week pattern
        # The API's Week_1/Week_2 indicates which fortnightly pattern the area follows
        # Week 1 areas: Rubbish + Food & Garden (green lid)
        # Week 2 areas: Rubbish + Recycling (yellow lid)
        bins_this_week = []
        bins_next_week = []

        if collection_week == "1":
            bins_this_week = ["Rubbish (red lid)", "Food & Garden (green lid)"]
            bins_next_week = ["Rubbish (red lid)", "Recycling (yellow lid)"]
        elif collection_week == "2":
            bins_this_week = ["Rubbish (red lid)", "Recycling (yellow lid)"]
            bins_next_week = ["Rubbish (red lid)", "Food & Garden (green lid)"]
        else:
            bins_this_week = ["Rubbish (red lid)", "Check your council schedule"]

        return {
            "address": address,
            "postcode": postcode,
            "collection_day": collection_day,
            "collection_week": collection_week,
            "current_week": current_week,
            "is_collection_week": collection_week == str(current_week) if collection_week != "Unknown" else None,
            "night_before": night_before,
            "bins_this_week": bins_this_week,
            "bins_next_week": bins_next_week
        }

    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

# Example usage
if __name__ == "__main__":
    print("=== City of Casey Bin Collection Lookup ===\n")
    address = input("Enter your address (e.g., 2 Patrick Northeast Drive, Narre Warren, VIC): ").strip()

    if not address:
        print("Error: No address provided.")
        exit(1)

    result = get_casey_waste_services(address)

    if "error" in result:
        print(f"\nError: {result['error']}")
    else:
        print("\n=== City of Casey Waste Collection Info ===")
        print(f"Address: {result['address']}")
        print(f"Postcode: {result['postcode']}")
        print(f"Collection Day: {result['collection_day']}")
        print(f"Collection Week: Week {result['collection_week']}")
        print(f"Current Week: Week {result['current_week']}")

        if result['is_collection_week']:
            print(f"\n✓ This is your collection week!")
            print(f"Put bins out: {result['night_before']} night")
            print(f"Collection: {result['collection_day']}")
            print(f"\nBins to put out:")
            for bin_type in result['bins_this_week']:
                print(f"  • {bin_type}")
        elif result['is_collection_week'] is False:
            print(f"\n✗ Not your collection week.")
            print(f"Next collection: {result['collection_day']} (Week {result['collection_week']})")
            print(f"\nNext week's bins:")
            for bin_type in result['bins_next_week']:
                print(f"  • {bin_type}")
        print("=" * 43)
