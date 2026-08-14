from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.config import get_settings


class AutoDevClient:
    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.auto_dev_api_key.get_secret_value()
        self.base_url = "https://api.auto.dev"

    def decode_vin(self, vin: str) -> dict[str, Any]:
        response = httpx.get(
            f"{self.base_url}/vin/{vin}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()

    def search_listings(
        self,
        *,
        make: str | None = None,
        model: str | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        min_mileage: int | None = None,
        max_mileage: int | None = None,
        location: str | None = None,
        limit: int | None = None,
    ) -> Any:
        params: dict[str, Any] = {}

        def add_range_param(param_name: str, min_value: int | None, max_value: int | None) -> None:
            if min_value is not None and max_value is not None:
                params[param_name] = f"{min_value}-{max_value}"
            elif min_value is not None:
                params[param_name] = f"{min_value}-"
            elif max_value is not None:
                params[param_name] = f"-{max_value}"

        if make is not None:
            params["vehicle.make"] = make
        if model is not None:
            params["vehicle.model"] = model

        add_range_param("vehicle.year", min_year, max_year)
        add_range_param("retailListing.price", min_price, max_price)
        add_range_param("retailListing.miles", min_mileage, max_mileage)

        if limit is not None:
            params["limit"] = limit

        # Auto.dev V2 geographic filtering uses zip + distance. A free-form city/state
        # string is not reliably convertible to a ZIP code, so we omit it here until a
        # real ZIP is supplied.
        if location is not None and re.fullmatch(r"\d{5}", location.strip()):
            params["zip"] = location.strip()

        response = httpx.get(
            f"{self.base_url}/listings",
            params=params,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()
