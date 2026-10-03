from app.models import SearchRequest, UserSearchIntent


class SearchPlanner:
    DEFAULT_MAX_REQUESTS = 10

    def __init__(self, max_requests: int = DEFAULT_MAX_REQUESTS) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1")
        self.max_requests = max_requests

    def plan(self, intent: UserSearchIntent) -> list[SearchRequest]:
        base_request = intent.search_request
        if base_request.body_style is None:
            body_styles = _unique_values(intent.body_styles)
            if body_styles:
                base_request = base_request.model_copy(
                    update={"body_style": ",".join(body_styles)}
                )
        makes = _unique_values(intent.makes) if base_request.make is None else []
        models = _unique_values(intent.models) if base_request.model is None else []

        if makes and models:
            if len(makes) == 1 and len(models) == 1:
                return [
                    base_request.model_copy(
                        update={"make": makes[0], "model": models[0]}
                    )
                ]
            if len(makes) > 1 and len(models) > 1:
                models = []
            else:
                return [base_request]

        alternatives = makes or models
        if not alternatives:
            return [base_request]

        field = "make" if makes else "model"
        requests: list[SearchRequest] = []
        seen: set[str] = set()
        for value in alternatives[: self.max_requests]:
            request = base_request.model_copy(update={field: value})
            key = request.model_dump_json()
            if key not in seen:
                requests.append(request)
                seen.add(key)
        return requests


def _unique_values(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if normalized and key not in seen:
            unique.append(normalized)
            seen.add(key)
    return unique
