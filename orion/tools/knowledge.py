from langchain_huggingface import HuggingFaceEndpointEmbeddings
from orion.config import settings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

class Knowledge(object):
    def __init__(self):
        self.embeddings = HuggingFaceEndpointEmbeddings(
            provider="hf-inference",
            huggingfacehub_api_token=settings.embedding.token,
            model=settings.embedding.model
        )

        self.vectorstore = QdrantVectorStore.from_existing_collection(
            embedding=self.embeddings,
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            collection_name=settings.qdrant.collection
        )

    def query(self, query):
        docs = self.vectorstore.similarity_search(query, k=3)

        context = ""
        for doc in docs:
            context += doc.page_content

        return context