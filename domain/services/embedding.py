from abc import ABC, abstractmethod


class IEmbeddingProvider(ABC):
    @abstractmethod
    def embed_document(self, text: str) -> list[float]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...
