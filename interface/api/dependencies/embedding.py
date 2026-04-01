from infrastructure.embedding import VertexEmbeddingProvider


def get_embedding_provider() -> VertexEmbeddingProvider:
    return VertexEmbeddingProvider()
