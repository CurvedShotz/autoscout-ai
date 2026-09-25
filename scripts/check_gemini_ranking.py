"""Manual live Gemini ranking check; not collected by pytest."""

from pathlib import Path
import sys


API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
sys.path.insert(0, str(API_ROOT))

from app.models import SearchRequest, VehicleListing  # noqa: E402
from app.services.gemini_ranking import GeminiRankingService  # noqa: E402


def main() -> None:
    search_request = SearchRequest(
        make="Toyota",
        model="RAV4",
        min_year=2019,
        max_price=32_000,
        max_mileage=70_000,
        location="Austin, TX",
    )

    listings = [
        VehicleListing(
            vin="2T3W1RFV5KW012341",
            year=2022,
            make="Toyota",
            model="RAV4",
            trim="XLE Premium",
            body_style="SUV",
            drivetrain="AWD",
            engine="2.5L I4",
            transmission="8-speed automatic",
            fuel="Gasoline",
            price=29_400,
            mileage=31_200,
            city="Austin",
            state="TX",
            zip="78701",
            accident_count=0,
            has_accidents=False,
            owner_count=1,
            one_owner=True,
            usage_type="Personal",
        ),
        VehicleListing(
            vin="2T3R1RFV8MW023452",
            year=2021,
            make="Toyota",
            model="RAV4",
            trim="XLE",
            body_style="SUV",
            drivetrain="AWD",
            engine="2.5L I4",
            transmission="8-speed automatic",
            fuel="Gasoline",
            price=25_800,
            mileage=44_500,
            city="Round Rock",
            state="TX",
            zip="78664",
            accident_count=0,
            has_accidents=False,
            owner_count=2,
            one_owner=False,
            usage_type="Personal",
        ),
        VehicleListing(
            vin="2T3H1RFV2NW034563",
            year=2023,
            make="Toyota",
            model="RAV4",
            trim="LE",
            body_style="SUV",
            drivetrain="FWD",
            engine="2.5L I4",
            transmission="8-speed automatic",
            fuel="Gasoline",
            price=27_900,
            mileage=18_700,
            city="Cedar Park",
            state="TX",
            zip="78613",
            accident_count=0,
            has_accidents=False,
            owner_count=1,
            one_owner=True,
            usage_type="Personal",
        ),
        VehicleListing(
            vin="2T3J1RFV6LW045674",
            year=2020,
            make="Toyota",
            model="RAV4",
            trim="LE",
            body_style="SUV",
            drivetrain="FWD",
            engine="2.5L I4",
            transmission="8-speed automatic",
            fuel="Gasoline",
            price=17_900,
            mileage=68_400,
            city="San Marcos",
            state="TX",
            zip="78666",
            accident_count=2,
            has_accidents=True,
            owner_count=3,
            one_owner=False,
            usage_type="Personal",
        ),
        VehicleListing(
            vin="2T3D1RFV9NW056785",
            year=2022,
            make="Toyota",
            model="RAV4",
            trim="XLE Hybrid",
            body_style="SUV",
            drivetrain="AWD",
            engine="2.5L Hybrid",
            transmission="CVT",
            fuel="Hybrid",
            price=31_700,
            mileage=27_600,
            city="Georgetown",
            state="TX",
            zip="78626",
            accident_count=1,
            has_accidents=True,
            owner_count=1,
            one_owner=True,
            usage_type="Personal",
        ),
    ]

    rankings = GeminiRankingService().rank_listings(search_request, listings)
    for item in rankings.rankings:
        print(f"Rank {item.rank} | VIN {item.vin} | Score {item.score:g}")
        print(f"Reason: {item.reason}")


if __name__ == "__main__":
    main()
