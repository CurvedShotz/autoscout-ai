import pytest

from app.models import SearchRequest, UserSearchIntent
from app.services.search_planner import SearchPlanner


def test_plain_hard_request_produces_one_plan() -> None:
    request = SearchRequest(make="Honda", min_year=2018, max_price=20_000)

    assert SearchPlanner().plan(UserSearchIntent(search_request=request)) == [request]


def test_alternative_makes_produce_separate_requests() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(location="Dallas"),
        makes=["Honda", "Toyota"],
    )

    assert SearchPlanner().plan(intent) == [
        SearchRequest(make="Honda", location="Dallas"),
        SearchRequest(make="Toyota", location="Dallas"),
    ]


def test_explicit_single_make_and_model_produce_one_plan() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(),
        makes=["Honda"],
        models=["Civic"],
    )

    assert SearchPlanner().plan(intent) == [SearchRequest(make="Honda", model="Civic")]


def test_empty_hard_filters_produce_one_broad_plan() -> None:
    assert SearchPlanner().plan(
        UserSearchIntent(search_request=SearchRequest())
    ) == [SearchRequest()]


def test_duplicate_alternatives_are_removed_case_insensitively() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(),
        makes=["Honda", "Toyota", " honda ", "Toyota"],
    )

    assert SearchPlanner().plan(intent) == [
        SearchRequest(make="Honda"),
        SearchRequest(make="Toyota"),
    ]


def test_alternative_models_expand_while_preserving_hard_make() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(make="Toyota", location="Austin"),
        models=["Camry", "Corolla"],
    )

    assert SearchPlanner().plan(intent) == [
        SearchRequest(make="Toyota", model="Camry", location="Austin"),
        SearchRequest(make="Toyota", model="Corolla", location="Austin"),
    ]


def test_mixed_hard_filters_are_preserved_across_alternative_makes() -> None:
    hard_request = SearchRequest(
        location="Dallas",
        min_year=2018,
        max_year=2023,
        min_price=5_000,
        max_price=25_000,
        min_mileage=10_000,
        max_mileage=80_000,
    )
    intent = UserSearchIntent(
        search_request=hard_request,
        makes=["Honda", "Toyota"],
        target_price=15_000,
        target_mileage=50_000,
        body_styles=["sedan"],
        preferences=["reliable"],
    )

    plans = SearchPlanner().plan(intent)

    assert len(plans) == 2
    for plan, make in zip(plans, ["Honda", "Toyota"]):
        assert plan == hard_request.model_copy(
            update={"make": make, "body_style": "sedan"}
        )


def test_multiple_alternative_makes_and_models_expand_makes_only() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(max_price=30_000),
        makes=["Honda", "Toyota"],
        models=["Civic", "Camry"],
    )

    assert SearchPlanner().plan(intent) == [
        SearchRequest(make="Honda", max_price=30_000),
        SearchRequest(make="Toyota", max_price=30_000),
    ]


def test_ambiguous_alternatives_respect_fanout_cap() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(),
        makes=["Honda", "Toyota", "Ford"],
        models=["Civic", "Camry"],
    )

    assert SearchPlanner(max_requests=2).plan(intent) == [
        SearchRequest(make="Honda"),
        SearchRequest(make="Toyota"),
    ]


def test_request_fanout_is_capped() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(),
        makes=["Honda", "Toyota", "Ford"],
    )

    assert SearchPlanner(max_requests=2).plan(intent) == [
        SearchRequest(make="Honda"),
        SearchRequest(make="Toyota"),
    ]


def test_request_fanout_limit_must_be_positive() -> None:
    with pytest.raises(ValueError, match="max_requests must be at least 1"):
        SearchPlanner(max_requests=0)


def test_body_style_alternative_is_preserved_in_provider_request() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(),
        body_styles=["sedan"],
    )

    assert SearchPlanner().plan(intent) == [SearchRequest(body_style="sedan")]


def test_body_style_and_mileage_constraint_are_preserved() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(max_mileage=60_000),
        body_styles=["sedan"],
    )

    assert SearchPlanner().plan(intent) == [
        SearchRequest(body_style="sedan", max_mileage=60_000)
    ]


def test_body_style_is_preserved_with_make_and_model() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(make="Honda", model="Civic"),
        body_styles=["Sedan"],
    )

    assert SearchPlanner().plan(intent) == [
        SearchRequest(make="Honda", model="Civic", body_style="Sedan")
    ]


def test_multiple_body_styles_use_provider_or_filter_without_fanout() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(max_mileage=60_000),
        body_styles=["sedan", "SUV", " SEDAN "],
    )

    assert SearchPlanner(max_requests=1).plan(intent) == [
        SearchRequest(body_style="sedan,SUV", max_mileage=60_000)
    ]


def test_no_body_style_preserves_existing_plan() -> None:
    intent = UserSearchIntent(
        search_request=SearchRequest(make="Honda", max_mileage=60_000)
    )

    assert SearchPlanner().plan(intent) == [intent.search_request]
