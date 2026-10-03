from pydantic import BaseModel, field_validator


class NaturalSearchRequest(BaseModel):
    query: str

    @field_validator("query")
    @classmethod
    def validate_query(cls, query: str) -> str:
        if not query.strip():
            raise ValueError("query must not be empty")
        return query
