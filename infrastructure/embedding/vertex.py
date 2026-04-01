from __future__ import annotations

import logging

from google.oauth2 import service_account
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from domain.services.embedding import IEmbeddingProvider
from infrastructure.config import settings
from infrastructure.runtime_warnings import apply_runtime_warning_filters

apply_runtime_warning_filters()


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
        self.model = GoogleGenerativeAIEmbeddings(
            model=self._model_name,
            credentials=creds,
            project=settings.google.project_id,
            location=settings.google.location,
            vertexai=True,
            output_dimensionality=self.output_dimensionality,
        )

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_document(self, text: str) -> list[float]:
        if not text:
            return []
        return self.model.embed_documents(
            [text],
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=self.output_dimensionality,
        )[0]

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return []
        return self.model.embed_query(
            text,
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=self.output_dimensionality,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.model.embed_documents(
            texts,
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=self.output_dimensionality,
        )
