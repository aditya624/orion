from collections import defaultdict

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from orion.config import settings
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http import models as rest

from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class Knowledge(object):
    def __init__(self):
        self.embeddings = HuggingFaceEndpointEmbeddings(
            provider="hf-inference",
            huggingfacehub_api_token=settings.embedding.token,
            model=settings.embedding.model,
            model_kwargs={"normalize": True, "truncate": True}
        )

        self.vectorstore = QdrantVectorStore.from_existing_collection(
            embedding=self.embeddings,
            url=settings.qdrant.url,
            api_key=settings.qdrant.api_key,
            collection_name=settings.qdrant.collection
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.qdrant.chunk_size, chunk_overlap=settings.qdrant.chunk_overlap
        )

    def query(self, query):
        docs = self.vectorstore.similarity_search(query, k=settings.qdrant.top_k)
        context = ""
        for doc in docs:
            page_content = doc.page_content
            metadata = doc.metadata

            context += f"# Title: {metadata['title']}\n"
            context += f"## Link: {metadata['source']}\n"
            context += f"## Chunk of Content:\n{page_content}\n\n"

        return context

    def check_validity(self, links: list):
        clean_link = defaultdict(list)
        for link in links:
            results = self.vectorstore.client.scroll(
                collection_name=self.vectorstore.collection_name,
                scroll_filter=rest.Filter(
                    must=[
                        rest.FieldCondition(
                            key="metadata.source",
                            match=rest.MatchValue(value=link)
                        )
                    ]
                ),
                limit=1
            )

            if results[0]:
                clean_link["exists"].append(link)
            else:
                clean_link["not_exists"].append(link)

        return clean_link

    def upload_link(self, links: list):
        try:
            clean_link = self.check_validity(links)
        except Exception as e:
            raise ValueError(f"Failed scroll from vectorstore: {e}")
        
        try:
            not_exist_links= clean_link["not_exists"]

            chunks = []
            if len(not_exist_links) > 0:
                loader = WebBaseLoader(not_exist_links)
                docs = loader.load()
                chunks = self.text_splitter.split_documents(docs)

        except Exception as e:
            raise ValueError(f"Failed to load documents: {e}")
        
        try:
            if len(chunks) > 0:
                self.vectorstore.add_documents(chunks)
        except Exception as e:
            raise ValueError(f"Failed add documents to vectorstore: {e}")
        
        return dict(clean_link)

        
