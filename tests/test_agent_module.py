import types
from datetime import datetime

import pytest


@pytest.fixture
def stub_settings():
    return types.SimpleNamespace(
        app_name="Test App",
        version="0.1.0",
        token="test-token",
        groq=types.SimpleNamespace(api_key="fake-key"),
        mongodb=types.SimpleNamespace(
            uri="mongodb://localhost",
            database="test_db",
            collection="chat_history",
            history_size=5,
            history_collection="histories",
        ),
    )


@pytest.fixture
def agent_module(monkeypatch, stub_settings):
    from orion.agent import agent as agent_module
    from orion.agent import history as history_module

    class FakeLangfuse:
        def __init__(self, *args, **kwargs):
            pass

    class FakeKnowledge:
        def __init__(self, prompt=None):
            self.prompt = prompt
            self.calls = []

        def query(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return "knowledge-response"

    class FakeStructuredTool:
        def __init__(self, func, args_schema, name, description):
            self.func = func
            self.args_schema = args_schema
            self.name = name
            self.description = description

        @classmethod
        def from_function(cls, func, args_schema=None, name=None, description=None):
            return cls(func, args_schema, name, description)

    class FakeBoundLLM:
        def __init__(self, tools):
            self.tools = tools
            self.invoke_calls = []

        def invoke(self, inputs, config):
            self.invoke_calls.append((inputs, config))
            return types.SimpleNamespace(content="llm-result")

    class FakeChatGroq:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.bound_tools = None

        def bind_tools(self, tools):
            self.bound_tools = tools
            return FakeBoundLLM(tools)

    class FakeHistory:
        instances = []

        def __init__(self, session_id, connection_string, database_name, collection_name, history_size):
            self.session_id = session_id
            self.connection_string = connection_string
            self.database_name = database_name
            self.collection_name = collection_name
            self.history_size = history_size
            self.messages = []
            self.__class__.instances.append(self)

        def add_user_message(self, message):
            self.messages.append(("user", message))

        def add_ai_message(self, message):
            self.messages.append(("ai", message))

    def fake_load_prompt(settings_obj, langfuse):
        return {
            "agent": {
                "config": {"model": "stub-model"},
                "prompt": "Today is {current_date}"
            },
            "knowledge": {
                "config": {"name": "knowledge-tool"},
                "description": "Access knowledge base"
            },
        }

    class KnowledgeArgs(types.SimpleNamespace):
        pass

    def fake_get_args_schema(prompt):
        return {"knowledge": KnowledgeArgs}

    class FakeGraph:
        def __init__(self, llm):
            self.llm = llm
            self.calls = []

        def invoke(self, state, config):
            self.calls.append((state, config))
            return {"messages": [types.SimpleNamespace(content="graph-answer")]} 

    def fake_graph_builder(self):
        llm_with_tools = self.model.bind_tools(self.bindtools)
        return FakeGraph(llm_with_tools)

    class FakeCursor:
        def __init__(self, records):
            self._records = list(records)

        def sort(self, field, direction):
            reverse = direction in (-1, "DESC")
            self._records.sort(
                key=lambda record: record.get(field) or datetime.min,
                reverse=reverse,
            )
            return self

        def skip(self, count):
            self._records = self._records[count:]
            return self

        def limit(self, count):
            self._records = self._records[:count]
            return self

        def __iter__(self):
            return iter(self._records)

    class FakeCollection:
        def __init__(self):
            self.records = []

        def insert_one(self, document):
            self.records.append(document)

        def find(self, query):
            return FakeCursor(
                record
                for record in self.records
                if record.get("user_id") == query.get("user_id")
                and record.get("session_id") == query.get("session_id")
            )

    class FakeDatabase:
        def __init__(self):
            self.collections = {}

        def __getitem__(self, name):
            if name not in self.collections:
                self.collections[name] = FakeCollection()
            return self.collections[name]

    class FakeMongoClient:
        instances = []

        def __init__(self, uri):
            self.uri = uri
            self.databases = {}
            self.__class__.instances.append(self)

        def __getitem__(self, name):
            if name not in self.databases:
                self.databases[name] = FakeDatabase()
            return self.databases[name]

    monkeypatch.setattr(agent_module, "Langfuse", FakeLangfuse)
    monkeypatch.setattr(agent_module, "Knowledge", FakeKnowledge)
    monkeypatch.setattr(agent_module, "StructuredTool", FakeStructuredTool)
    monkeypatch.setattr(agent_module, "ChatGroq", FakeChatGroq)
    monkeypatch.setattr(agent_module, "MongoDBChatMessageHistory", FakeHistory)
    monkeypatch.setattr(agent_module, "load_prompt", fake_load_prompt)
    monkeypatch.setattr(agent_module, "get_args_schema", fake_get_args_schema)
    monkeypatch.setattr(agent_module, "settings", stub_settings)
    monkeypatch.setattr(agent_module.Agent, "graph_builder", fake_graph_builder)
    monkeypatch.setattr(history_module, "settings", stub_settings)
    monkeypatch.setattr(history_module, "MongoClient", FakeMongoClient)

    agent_module.HistoryStore = history_module.HistoryStore
    agent_module._history_module = history_module

    return agent_module


def test_agent_initializes_with_structured_tool(agent_module):
    agent = agent_module.Agent()

    assert agent.model.kwargs["model"] == "stub-model"
    assert agent.model.kwargs["api_key"] == "fake-key"
    assert len(agent.bindtools) == 1

    tool = agent.bindtools[0]
    assert tool.name == "knowledge-tool"
    assert tool.description == "Access knowledge base"
    assert agent.model.bound_tools is agent.bindtools


def test_agent_generate_invokes_graph_and_updates_memory(agent_module):
    agent = agent_module.Agent()
    FakeHistory = agent_module.MongoDBChatMessageHistory
    FakeHistory.instances.clear()
    agent_module._history_module.MongoClient.instances.clear()

    answer = agent.generate("What is Orion?", session_id="session-123", user_id="user-42")

    assert answer == "graph-answer"
    graph = agent.graph
    assert graph.calls, "Graph should be invoked"
    state, config = graph.calls[-1]
    assert state["messages"] == [("human", "What is Orion?")]
    assert config["callbacks"], "Callbacks should be passed"

    history = FakeHistory.instances[-1]
    assert history.history_size == agent_module.settings.mongodb.history_size
    assert history.messages == [
        ("user", "What is Orion?"),
        ("ai", "graph-answer"),
    ]

    mongo_client = agent_module._history_module.MongoClient.instances[-1]
    database = mongo_client.databases[agent_module.settings.mongodb.database]
    collection = database.collections[agent_module.settings.mongodb.history_collection]
    assert len(collection.records) == 1
    document = collection.records[0]
    assert document["user_id"] == "user-42"
    assert document["session_id"] == "session-123"
    assert document["input"] == "What is Orion?"
    assert document["answer"] == "graph-answer"
    assert "created_at" in document


def test_agent_get_history_filters_by_user_and_session(agent_module):
    agent = agent_module.Agent()
    agent_module._history_module.MongoClient.instances.clear()

    answer = agent.generate("Question 1", session_id="session-1", user_id="user-1")
    assert answer == "graph-answer"
    agent.generate("Question 2", session_id="session-1", user_id="user-1")
    agent.generate("Question 3", session_id="session-1", user_id="user-2")

    history = agent.get_history(user_id="user-1", session_id="session-1")
    assert len(history) == 2
    assert [entry["input"] for entry in history] == ["Question 2", "Question 1"]
    for entry in history:
        assert entry["user_id"] == "user-1"
        assert entry["session_id"] == "session-1"
        assert entry["answer"] == "graph-answer"
        assert entry["created_at"] is not None

    oldest_first = agent.get_history(user_id="user-1", session_id="session-1", order="ASC")
    assert [entry["input"] for entry in oldest_first] == ["Question 1", "Question 2"]


def test_agent_get_history_rejects_invalid_order(agent_module):
    agent = agent_module.Agent()
    with pytest.raises(ValueError):
        agent.get_history(user_id="user-1", session_id="session-1", order="invalid")
