from app.services.auto_dev_client import AutoDevClient
from app.services.gemini_listing_risk_analyzer import GeminiListingRiskAnalyzer
from app.services.vehicle_listing_normalizer import normalize_listings


def main() -> None:
    try:
        raw_response = AutoDevClient().search_listings(
            make="Toyota",
            model="Camry",
            limit=30,
        )
        listings = normalize_listings(raw_response)
        assessments = GeminiListingRiskAnalyzer().analyze(listings)
    except Exception:
        print("Live listing risk analysis failed; provider details were not printed.")
        return

    if not assessments:
        print("No listings were returned for analysis.")
        return

    listings_by_vin = {
        listing.vin.strip().upper(): listing
        for listing in listings
        if listing.vin and listing.vin.strip()
    }
    for assessment in assessments:
        listing = listings_by_vin[assessment.vin.strip().upper()]
        vehicle = " ".join(
            str(value)
            for value in (listing.year, listing.make, listing.model)
            if value is not None
        )
        print(
            f"VIN: {assessment.vin} | Vehicle: {vehicle or 'unknown'} | "
            f"Price: {listing.price if listing.price is not None else 'n/a'} | "
            f"Mileage: {listing.mileage if listing.mileage is not None else 'n/a'} | "
            f"Risk: {assessment.risk_score}/100 ({assessment.risk_level.value})"
        )
        print(f"Signals: {', '.join(assessment.signals) if assessment.signals else 'none'}")
        print(f"Explanation: {assessment.explanation}")


if __name__ == "__main__":
    main()
