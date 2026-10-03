import sys
from dataclasses import dataclass

from app.models import ListingRiskAssessment, VehicleListing
from app.services.gemini_listing_risk_analyzer import GeminiListingRiskAnalyzer


@dataclass(frozen=True)
class Scenario:
    label: str
    listing: VehicleListing
    expected_min: int
    expected_max: int


SCENARIOS = [
    Scenario(
        "A. Normal recent used car",
        VehicleListing(
            vin="CAL-A-NORMAL-RECENT",
            year=2022,
            make="Toyota",
            model="Camry",
            trim="SE",
            price=24_500,
            mileage=32_000,
            accident_count=0,
            has_accidents=False,
            owner_count=1,
            one_owner=True,
            usage_type="personal",
        ),
        0,
        15,
    ),
    Scenario(
        "B. Normal older high-mileage car",
        VehicleListing(
            vin="CAL-B-OLDER-HIGH-MILES",
            year=2012,
            make="Toyota",
            model="Camry",
            trim="LE",
            price=7_900,
            mileage=148_000,
            accident_count=0,
            has_accidents=False,
            owner_count=2,
            usage_type="personal",
        ),
        0,
        25,
    ),
    Scenario(
        "C. Missing history",
        VehicleListing(
            vin="CAL-C-MISSING-HISTORY",
            year=2021,
            make="Honda",
            model="Accord",
            trim="EX",
            price=22_000,
            mileage=42_000,
        ),
        10,
        45,
    ),
    Scenario(
        "D. Accident history",
        VehicleListing(
            vin="CAL-D-ACCIDENTS",
            year=2021,
            make="Toyota",
            model="Camry",
            trim="XLE",
            price=22_500,
            mileage=39_000,
            accident_count=2,
            has_accidents=True,
            owner_count=1,
            one_owner=True,
            usage_type="personal",
        ),
        10,
        45,
    ),
    Scenario(
        "E. Extreme low-price outlier",
        VehicleListing(
            vin="CAL-E-PRICE-OUTLIER",
            year=2022,
            make="Toyota",
            model="Camry",
            trim="SE",
            price=399,
            mileage=34_000,
            accident_count=0,
            has_accidents=False,
            owner_count=1,
            one_owner=True,
            usage_type="personal",
        ),
        75,
        100,
    ),
    Scenario(
        "F. Very new car with implausibly high mileage",
        VehicleListing(
            vin="CAL-F-NEW-HIGH-MILES",
            year=2025,
            make="Honda",
            model="Accord",
            trim="Sport",
            price=21_000,
            mileage=285_000,
            accident_count=0,
            has_accidents=False,
            owner_count=1,
            one_owner=True,
            usage_type="personal",
        ),
        # 285k miles on a 2025 vehicle warrants strong caution but is not proof of fraud.
        25,
        80,
    ),
    Scenario(
        "G. Cheap older high-mileage car at plausible price",
        VehicleListing(
            vin="CAL-G-CHEAP-OLD",
            year=2009,
            make="Toyota",
            model="Camry",
            trim="Base",
            price=3_900,
            mileage=205_000,
            accident_count=0,
            has_accidents=False,
            owner_count=3,
            usage_type="personal",
        ),
        0,
        25,
    ),
    Scenario(
        "H. Missing mileage/specifications",
        VehicleListing(
            vin="CAL-H-MISSING-SPECS",
            year=2024,
            make="Toyota",
            model="Camry",
            price=25_000,
        ),
        10,
        45,
    ),
]

RISK_FACTOR_PHRASES: dict[str, tuple[str, ...]] = {
    "price": (
        "placeholder",
        "unusually low price",
        "extreme outlier",
        "price discrepancy",
        "pricing anomaly",
        "price cannot be verified",
    ),
    "mileage": (
        "extreme mileage",
        "implausible mileage",
        "unusually high mileage",
        "unusually low mileage",
        "mileage anomaly",
        "mileage is missing",
        "missing mileage",
    ),
    "accident": (
        "accident history noted",
        "accident history present",
        "accident is reported",
        "accidents are reported",
        "reported accident history",
        "accident count",
        "multiple accidents",
    ),
    "ownership": (
        "high owner count",
        "unusually many owners",
    ),
    "history": (
        "missing history",
        "history is missing",
        "history is unavailable",
        "history data is missing",
        "history cannot be verified",
    ),
    "specification": (
        "missing drivetrain",
        "missing engine",
        "missing transmission",
        "missing specification",
        "missing specifications",
        "specifications are missing",
    ),
}


def _explanation_risk_factors(explanation: str) -> set[str]:
    text = explanation.casefold()
    return {
        factor
        for factor, phrases in RISK_FACTOR_PHRASES.items()
        if any(phrase in text for phrase in phrases)
    }


def _signal_risk_factors(signals: list[str]) -> set[str]:
    return _explanation_risk_factors(" ".join(signals))


def explanation_signal_mismatches(assessment: ListingRiskAssessment) -> set[str]:
    return _explanation_risk_factors(assessment.explanation) - _signal_risk_factors(
        assessment.signals
    )


def _assessment_map(
    assessments: list[ListingRiskAssessment],
) -> dict[str, ListingRiskAssessment]:
    return {assessment.vin.upper(): assessment for assessment in assessments}


def _print_check(label: str, passed: bool, detail: str) -> bool:
    print(f"{'PASS' if passed else 'FAIL'} | {label}: {detail}")
    return passed


def main() -> bool:
    listings = [scenario.listing for scenario in SCENARIOS]
    try:
        assessments = GeminiListingRiskAnalyzer().analyze(listings)
    except Exception:
        print("Calibration failed; Gemini details were not printed.")
        return False

    by_vin = _assessment_map(assessments)
    print("Listing risk calibration (controlled candidate set)")
    print(
        "Scenario | VIN | Year Make Model | Price | Mileage | Score | Level | "
        "Signals | Explanation"
    )
    print("-" * 180)

    passed = 0
    total = 0
    for scenario in SCENARIOS:
        listing = scenario.listing
        assessment = by_vin[listing.vin.upper()]
        vehicle = " ".join(
            str(value)
            for value in (listing.year, listing.make, listing.model)
            if value is not None
        )
        signals = "; ".join(assessment.signals) if assessment.signals else "none"
        print(
            f"{scenario.label} | {assessment.vin} | {vehicle} | "
            f"{listing.price if listing.price is not None else 'n/a'} | "
            f"{listing.mileage if listing.mileage is not None else 'n/a'} | "
            f"{assessment.risk_score} | {assessment.risk_level.value} | "
            f"{signals} | {assessment.explanation}"
        )

        in_band = scenario.expected_min <= assessment.risk_score <= scenario.expected_max
        total += 1
        passed += _print_check(
            f"{scenario.label} expected band",
            in_band,
            f"{assessment.risk_score} in {scenario.expected_min}-{scenario.expected_max}",
        )

        uncited_factors = explanation_signal_mismatches(assessment)
        total += 1
        passed += _print_check(
            f"{scenario.label} explanation/signal consistency",
            not uncited_factors,
            (
                "risk factors are represented in signals"
                if not uncited_factors
                else f"explanation risk factors absent from signals: {', '.join(sorted(uncited_factors))}"
            ),
        )

    scores = [assessment.risk_score for assessment in assessments]
    normal_labels = {
        "A. Normal recent used car",
        "B. Normal older high-mileage car",
        "G. Cheap older high-mileage car at plausible price",
    }
    normal_scores = [
        by_vin[scenario.listing.vin.upper()].risk_score
        for scenario in SCENARIOS
        if scenario.label in normal_labels
    ]
    accident_score = by_vin["CAL-D-ACCIDENTS"].risk_score
    old_high_mile_scores = [
        by_vin["CAL-B-OLDER-HIGH-MILES"].risk_score,
        by_vin["CAL-G-CHEAP-OLD"].risk_score,
    ]
    outlier_score = by_vin["CAL-E-PRICE-OUTLIER"].risk_score
    normal_max = max(normal_scores)

    total += 1
    passed += _print_check(
        "accident history alone is not high risk",
        accident_score < 70,
        f"observed score {accident_score} is below 70",
    )
    total += 1
    passed += _print_check(
        "plausible old/high-mileage listings are not high risk",
        all(score < 70 for score in old_high_mile_scores),
        f"observed scores {old_high_mile_scores} are below 70",
    )
    outlier_separation = outlier_score - normal_max
    total += 1
    passed += _print_check(
        "placeholder-like price separates from normal listings",
        outlier_separation >= 40,
        f"outlier {outlier_score} minus highest normal {normal_max} = {outlier_separation}",
    )

    print(
        f"Overall: {passed}/{total} checks passed; "
        f"score spread {min(scores)}-{max(scores)}; "
        f"{len(set(scores))} unique scores across {len(scores)} candidates."
    )
    return passed == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
