import sys
import types

import pytest

from langchain_core.documents import Document


# Provide a lightweight stub for the optional dependency used in Knowledge.
_semantic_module = types.ModuleType("langchain_experimental.text_splitter")


class _SemanticChunkerStub:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.calls = []
        self.return_value = []

    def split_documents(self, docs):
        self.calls.append(docs)
        return self.return_value


_semantic_module.SemanticChunker = _SemanticChunkerStub
sys.modules.setdefault("langchain_experimental", types.ModuleType("langchain_experimental"))
sys.modules["langchain_experimental.text_splitter"] = _semantic_module

from orion.tools.knowledge import Knowledge
from orion.config import settings


class DummySplitter:
    def __init__(self):
        self.calls = []
        self.return_value = []

    def split_documents(self, docs):
        self.calls.append(docs)
        return self.return_value


class DummyClient:
    def __init__(self):
        self.scroll_calls = []
        self.scroll_results = []

    def scroll(self, **kwargs):
        self.scroll_calls.append(kwargs)
        if not self.scroll_results:
            raise AssertionError("No scroll result configured")
        return self.scroll_results.pop(0)


class DummyVectorStore:
    def __init__(self):
        self.collection_name = "collection"
        self.client = DummyClient()
        self.similarity_search_args = []
        self.similarity_search_result = []
        self.add_documents_calls = []

    def similarity_search(self, query, k):
        self.similarity_search_args.append((query, k))
        return self.similarity_search_result

    def add_documents(self, docs):
        self.add_documents_calls.append(docs)


@pytest.fixture
def knowledge(monkeypatch):
    splitter = DummySplitter()
    vectorstore = DummyVectorStore()

    monkeypatch.setattr(
        "orion.tools.knowledge.HuggingFaceEndpointEmbeddings",
        lambda **_: object(),
    )
    monkeypatch.setattr("orion.tools.knowledge.ChatGroq", lambda **_: object())

    class DummyQdrantVectorStore:
        @classmethod
        def from_existing_collection(cls, *args, **kwargs):
            return vectorstore

    monkeypatch.setattr("orion.tools.knowledge.QdrantVectorStore", DummyQdrantVectorStore)
    monkeypatch.setattr(
        "orion.tools.knowledge.SemanticChunker",
        lambda *args, **kwargs: splitter,
    )

    class DummyChain:
        def __init__(self):
            self.calls = []

        def invoke(self, inputs, config=None):
            self.calls.append((inputs, config))
            return "dummy summary"

    dummy_chain = DummyChain()

    monkeypatch.setattr("orion.tools.knowledge.Knowledge.build_chain", lambda self: dummy_chain)

    loader_calls = []

    def loader_factory(urls):
        loader_calls.append(urls)

        class DummyLoader:
            def load(self_inner):
                return [
                    Document(
                        page_content="page content",
                        metadata={"source": urls[0], "title": "Loaded Title"},
                    )
                ]

        return DummyLoader()

    monkeypatch.setattr("orion.tools.knowledge.WebBaseLoader", loader_factory)

    prompt = {
        "chain": {
            "config": {"model": "dummy-model"},
            "prompt": "{input}",
        }
    }

    return Knowledge(prompt=prompt), vectorstore, splitter, loader_calls


def test_query_builds_context(knowledge):
    knowledge_instance, vectorstore, _, _ = knowledge
    vectorstore.similarity_search_result = [
        Document(
            page_content="content one",
            metadata={"title": "First", "source": "https://first.example"},
        ),
        Document(
            page_content="content two",
            metadata={"title": "Second", "source": "https://second.example"},
        ),
    ]

    result = knowledge_instance.query("test query")

    expected = (
        "# Title: First\n"
        "## Link: https://first.example\n"
        "## Chunk of Content:\ncontent one\n\n"
        "# Title: Second\n"
        "## Link: https://second.example\n"
        "## Chunk of Content:\ncontent two\n\n"
    )

    assert result == expected
    assert vectorstore.similarity_search_args == [("test query", settings.qdrant.top_k)]


def test_check_validity_categorizes_links(knowledge):
    knowledge_instance, vectorstore, _, _ = knowledge
    vectorstore.client.scroll_results = [([{"id": "exists"}], None), ([], None)]

    result = knowledge_instance.check_validity([
        "https://first.example",
        "https://second.example",
    ])

    assert result["exists"] == ["https://first.example"]
    assert result["not_exists"] == ["https://second.example"]
    assert len(vectorstore.client.scroll_calls) == 2
    for call in vectorstore.client.scroll_calls:
        assert call["collection_name"] == vectorstore.collection_name


def test_upload_link_adds_new_documents(knowledge):
    knowledge_instance, vectorstore, splitter, loader_calls = knowledge
    vectorstore.client.scroll_results = [([{"id": "exists"}], None), ([], None)]
    splitter.return_value = [
        Document(page_content="chunk one", metadata={"chunk": 1}),
        Document(page_content="chunk two", metadata={"chunk": 2}),
    ]

    result = knowledge_instance.upload_link([
        "https://first.example",
        "https://second.example",
    ])

    assert result == {
        "exists": ["https://first.example"],
        "not_exists": ["https://second.example"],
    }
    assert loader_calls == [["https://second.example"]]
    assert splitter.calls
    first_doc = splitter.calls[0][0]
    assert first_doc.metadata["source"] == "https://second.example"
    assert vectorstore.add_documents_calls == [
        [
            Document(page_content="chunk one", metadata={"chunk": 1}),
            Document(page_content="chunk two", metadata={"chunk": 2}),
        ]
    ]


def test_upload_link_wraps_check_validity_errors(monkeypatch, knowledge):
    knowledge_instance, _, _, _ = knowledge

    def failing_check(_):
        raise RuntimeError("boom")

    monkeypatch.setattr(knowledge_instance, "check_validity", failing_check)

    with pytest.raises(ValueError, match="Failed scroll from vectorstore: boom"):
        knowledge_instance.upload_link(["https://error.example"])
