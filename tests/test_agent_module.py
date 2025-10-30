import types
from datetime import datetime, timedelta

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

    class FakeHistoryStore:
        _counter = 0

        def __init__(self):
            self.saved_records = []
            self.list_calls = []
            self.get_history_calls = []

        def save(
            self,
            *,
            user_id,
            session_id,
            input_text,
            answer,
            created_at=None,
        ):
            if created_at is None:
                created_at = datetime(2024, 1, 1) + timedelta(minutes=self.__class__._counter)
            self.__class__._counter += 1

            record = {
                "user_id": user_id,
                "session_id": session_id,
                "input": input_text,
                "answer": answer,
                "created_at": created_at,
            }
            self.saved_records.append(record)
            return record

        def list(
            self,
            *,
            user_id,
            session_id,
            order="DESC",
            offset=0,
            limit=None,
        ):
            if order not in {"ASC", "DESC"}:
                raise ValueError("order must be either 'ASC' or 'DESC'")
            if offset < 0:
                raise ValueError("offset must be a non-negative integer")
            if limit is not None and limit <= 0:
                raise ValueError("limit must be greater than zero when provided")

            self.list_calls.append(
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "order": order,
                    "offset": offset,
                    "limit": limit,
                }
            )

            records = [
                record
                for record in self.saved_records
                if record["user_id"] == user_id and record["session_id"] == session_id
            ]

            records.sort(key=lambda record: record["created_at"], reverse=(order == "DESC"))
            if offset:
                records = records[offset:]
            if limit is not None:
                records = records[:limit]
            return list(records)

        def get_history_for_messages(self, user_id, session_id, size):
            self.get_history_calls.append(
                {"user_id": user_id, "session_id": session_id, "size": size}
            )

            records = [
                record
                for record in self.saved_records
                if record["user_id"] == user_id and record["session_id"] == session_id
            ]
            records.sort(key=lambda record: record["created_at"])
            records = records[-size:]

            messages = []
            for record in records:
                messages.append({"role": "user", "content": record["input"]})
                messages.append({"role": "assistant", "content": record["answer"]})
            return messages

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

    monkeypatch.setattr(agent_module, "Langfuse", FakeLangfuse)
    monkeypatch.setattr(agent_module, "Knowledge", FakeKnowledge)
    monkeypatch.setattr(agent_module, "StructuredTool", FakeStructuredTool)
    monkeypatch.setattr(agent_module, "ChatGroq", FakeChatGroq)
    monkeypatch.setattr(agent_module, "HistoryStore", FakeHistoryStore)
    monkeypatch.setattr(agent_module, "load_prompt", fake_load_prompt)
    monkeypatch.setattr(agent_module, "get_args_schema", fake_get_args_schema)
    monkeypatch.setattr(agent_module, "settings", stub_settings)
    monkeypatch.setattr(agent_module.Agent, "graph_builder", fake_graph_builder)

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
    FakeHistoryStore = agent_module.HistoryStore
    FakeHistoryStore._counter = 0
    agent.history_store.saved_records.clear()
    agent.history_store.get_history_calls.clear()

    answer = agent.generate("What is Orion?", session_id="session-123", user_id="user-42")

    assert answer == "graph-answer"
    graph = agent.graph
    assert graph.calls, "Graph should be invoked"
    state, config = graph.calls[-1]
    assert state["messages"][-1] == {"role": "user", "content": "What is Orion?"}
    assert config["callbacks"], "Callbacks should be passed"

    history_instance = agent.history_store
    assert history_instance.get_history_calls[-1]["size"] == agent_module.settings.mongodb.history_size

    assert len(history_instance.saved_records) == 1
    document = history_instance.saved_records[0]
    assert document["user_id"] == "user-42"
    assert document["session_id"] == "session-123"
    assert document["input"] == "What is Orion?"
    assert document["answer"] == "graph-answer"
    assert "created_at" in document


def test_agent_get_history_filters_by_user_and_session(agent_module):
    agent = agent_module.Agent()
    FakeHistoryStore = agent_module.HistoryStore
    FakeHistoryStore._counter = 0
    agent.history_store.saved_records.clear()
    agent.history_store.get_history_calls.clear()

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
