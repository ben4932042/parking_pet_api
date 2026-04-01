from __future__ import annotations

import logging

import vertexai
from google.oauth2 import service_account
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

from domain.services.embedding import IEmbeddingProvider
from infrastructure.config import settings


class VertexEmbeddingProvider(IEmbeddingProvider):
    def __init__(
        self,
        *,
        model_name: str = "text-embedding-005",
        output_dimensionality: int = 768,
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self._model_name = model_name
        self.output_dimensionality = output_dimensionality

        creds = service_account.Credentials.from_service_account_file(
            settings.google.service_account_file,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        vertexai.init(
            project=settings.google.project_id,
            location=settings.google.location,
            credentials=creds,
        )
        self.model = TextEmbeddingModel.from_pretrained(self._model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_document(self, text: str) -> list[float]:
        return self._embed_texts([text], task_type="RETRIEVAL_DOCUMENT")[0]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_texts([text], task_type="RETRIEVAL_QUERY")[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        inputs = [
            TextEmbeddingInput(text=text, task_type=task_type)
            for text in texts
        ]
        embeddings = self.model.get_embeddings(
            inputs,
            output_dimensionality=self.output_dimensionality,
        )
        return [embedding.values for embedding in embeddings]
