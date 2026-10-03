from app.services.auto_dev_client import AutoDevClient
from app.services.location_resolver_provider import get_location_resolver
from app.services.natural_search import NaturalSearchService
from app.services.listing_risk_provider import get_listing_risk_analyzer
from app.services.ranking_provider import get_ranking_service
from app.services.search_query_parser_provider import get_search_query_parser
from app.services.search_planner import SearchPlanner


def get_natural_search_service() -> NaturalSearchService:
    return NaturalSearchService(
        parser=get_search_query_parser(),
        planner=SearchPlanner(),
        auto_dev_client=AutoDevClient(),
        location_resolver=get_location_resolver(),
        ranking_service=get_ranking_service(),
        risk_analyzer=get_listing_risk_analyzer(),
    )
