import re
from collections import defaultdict

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from orion.config import settings
from langchain_qdrant import QdrantVectorStore
from qdrant_client.http import models as rest

from langchain_community.document_loaders import WebBaseLoader
from langchain.docstore.document import Document
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_experimental.text_splitter import SemanticChunker

from langfuse.langchain import CallbackHandler

class Knowledge(object):
    def __init__(self, prompt):

        self.prompt = prompt
        self.model = ChatGroq(
            model=self.prompt["chain"]["config"]["model"],
            api_key=settings.groq.api_key,
        )
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

        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": settings.qdrant.top_k}
        )

        self.semantic_splitter = SemanticChunker(
            self.embeddings, breakpoint_threshold_type="percentile", breakpoint_threshold_amount=80
        )

        self.chain = self.build_chain()

    def build_chain(self):
        prompt_template = PromptTemplate(
            input_variables=["input"],
            template=self.prompt["chain"]["prompt"]
        )

        chain = (
            prompt_template | self.model | StrOutputParser()
        ).with_config({"run_name": "chain"})

        return chain

    def query(self, query):
        docs = self.retriever.invoke(query, config={"callbacks":[CallbackHandler()]})
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

    def summary(self, raw):
        response = self.chain.invoke(
            {
                "input": raw
            },
            config={"callbacks":[CallbackHandler()]}
        )
        return response
    
    def reformat(self, docs):
        results = []
        for doc in docs:
            page_content = doc.page_content
            metadata = doc.metadata

            summ = self.summary(page_content)
            summ = re.sub(r"<think>.*?</think>", "", summ.strip(), flags=re.DOTALL)
            results.append(
                Document(
                    page_content=summ,
                    metadata=metadata
                )
            )

        return results

    def load_content(self, links: list):
        loader = WebBaseLoader(links)
        docs = loader.load()
        return docs
    
    def chucking(self, docs):
        chunks = self.semantic_splitter.split_documents(docs)
        return chunks

    def upload_link(self, links: list):
        try:
            clean_link = self.check_validity(links)
        except Exception as e:
            raise ValueError(f"Failed scroll from vectorstore: {e}")
        
        try:
            not_exist_links= clean_link["not_exists"]

            chunks = []
            if len(not_exist_links) > 0:
                docs = self.load_content(not_exist_links)
                docs = self.reformat(docs)
                chunks = self.chucking(docs)
        except Exception as e:
            raise ValueError(f"Failed to load documents: {e}")
        
        try:
            if len(chunks) > 0:
                self.vectorstore.add_documents(chunks)
        except Exception as e:
            raise ValueError(f"Failed add documents to vectorstore: {e}")
        
        return dict(clean_link)

        
