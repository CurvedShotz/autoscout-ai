from fastapi import APIRouter

from app.models import SearchRequest

router = APIRouter()


@router.post("/search", tags=["search"])
def search(request: SearchRequest) -> dict[str, object]:
    return request.model_dump(exclude_none=True)
