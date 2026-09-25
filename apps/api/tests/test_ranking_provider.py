from types import SimpleNamespace

import pytest

from app.services.ranking_provider import (
    UnsupportedRankingProviderError,
    get_ranking_service,
)


@pytest.mark.parametrize(
    ("provider", "service_class"),
    [
        ("gemini", "GeminiRankingService"),
        ("openai", "OpenAIRankingService"),
    ],
)
def test_factory_selects_configured_provider(monkeypatch, provider, service_class) -> None:
    expected_service = object()
    monkeypatch.setattr(
        "app.services.ranking_provider.get_settings",
        lambda: SimpleNamespace(ai_ranking_provider=provider),
    )
    monkeypatch.setattr(
        f"app.services.ranking_provider.{service_class}",
        lambda: expected_service,
    )

    assert get_ranking_service() is expected_service


def test_factory_rejects_unsupported_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.ranking_provider.get_settings",
        lambda: SimpleNamespace(ai_ranking_provider="anthropic"),
    )

    with pytest.raises(UnsupportedRankingProviderError, match="Unsupported AI ranking provider"):
        get_ranking_service()


def test_factory_normalizes_provider_name(monkeypatch) -> None:
    expected_service = object()
    monkeypatch.setattr(
        "app.services.ranking_provider.get_settings",
        lambda: SimpleNamespace(ai_ranking_provider=" GEMINI "),
    )
    monkeypatch.setattr(
        "app.services.ranking_provider.GeminiRankingService",
        lambda: expected_service,
    )

    assert get_ranking_service() is expected_service
