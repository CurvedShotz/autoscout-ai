from abc import ABC, abstractmethod

from app.models import UserSearchIntent


class SearchQueryParser(ABC):
    @abstractmethod
    def parse(self, query: str) -> UserSearchIntent:
        raise NotImplementedError