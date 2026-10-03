from app.services.gemini_search_parser import GeminiSearchQueryParser
from app.services.search_query_parser import SearchQueryParser


def get_search_query_parser() -> SearchQueryParser:
    return GeminiSearchQueryParser()
