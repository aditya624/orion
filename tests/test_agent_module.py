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

    class FakeChatGroq:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeLangfuse:
        def __init__(self, *args, **kwargs):
            pass

    class FakeKnowledge:
        def __init__(self, prompt=None):
            self.prompt = prompt
            self.upload_calls = []

        def upload_link(self, links):
            self.upload_calls.append(list(links))
            return {"exists": [], "not_exists": list(links)}

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
                "prompt": "Today is {current_date}",
            },
            "knowledge": {
                "config": {"name": "knowledge-tool"},
                "description": "Access knowledge base",
            },
        }

    class FakeGraph:
        def __init__(self, model):
            self.model = model
            self.calls = []

        async def ainvoke(self, state, config):
            self.calls.append((state, config))
            return {"messages": [types.SimpleNamespace(content="graph-answer")]}  # noqa: B950

    async def fake_graph_builder(self):
        return FakeGraph(self.model)

    monkeypatch.setattr(agent_module, "Langfuse", FakeLangfuse)
    monkeypatch.setattr(agent_module, "Knowledge", FakeKnowledge)
    monkeypatch.setattr(agent_module, "ChatGroq", FakeChatGroq)
    monkeypatch.setattr(agent_module, "HistoryStore", FakeHistoryStore)
    monkeypatch.setattr(agent_module, "load_prompt", fake_load_prompt)
    monkeypatch.setattr(agent_module, "settings", stub_settings)
    monkeypatch.setattr(agent_module.Agent, "graph_builder", fake_graph_builder)
    monkeypatch.setattr(agent_module, "get_date_and_time", lambda: "2024-01-01")

    return agent_module


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_agent_initializes_components(agent_module):
    agent = agent_module.Agent()

    assert agent.model.kwargs["model"] == "stub-model"
    assert agent.model.kwargs["api_key"] == "fake-key"
    assert agent.knowledge.prompt["knowledge"]["description"] == "Access knowledge base"
    assert isinstance(agent.history_store, agent_module.HistoryStore)


@pytest.mark.anyio("asyncio")
async def test_agent_generate_invokes_graph_and_updates_memory(agent_module):
    agent = agent_module.Agent()
    history = agent.history_store
    history.saved_records.clear()
    history.get_history_calls.clear()
    agent.graph = None

    answer = await agent.generate(
        "What is Orion?", session_id="session-123", user_id="user-42"
    )

    assert answer == "graph-answer"
    assert isinstance(agent.graph, object)
    assert agent.graph.calls, "Graph should receive a call"
    state, config = agent.graph.calls[-1]
    assert state["messages"][-1] == {"role": "user", "content": "What is Orion?"}
    assert config["callbacks"]
    assert history.get_history_calls[-1]["size"] == agent_module.settings.mongodb.history_size

    assert len(history.saved_records) == 1
    document = history.saved_records[0]
    assert document["user_id"] == "user-42"
    assert document["session_id"] == "session-123"
    assert document["input"] == "What is Orion?"
    assert document["answer"] == "graph-answer"


@pytest.mark.anyio("asyncio")
async def test_agent_get_history_filters_by_user_and_session(agent_module):
    agent = agent_module.Agent()
    history = agent.history_store
    history.saved_records.clear()

    await agent.generate("Question 1", session_id="session-1", user_id="user-1")
    await agent.generate("Question 2", session_id="session-1", user_id="user-1")
    await agent.generate("Question 3", session_id="session-1", user_id="user-2")

    recent = agent.get_history(user_id="user-1", session_id="session-1")
    assert [entry["input"] for entry in recent] == ["Question 2", "Question 1"]
    for entry in recent:
        assert entry["user_id"] == "user-1"
        assert entry["session_id"] == "session-1"
        assert entry["answer"] == "graph-answer"

    oldest_first = agent.get_history(user_id="user-1", session_id="session-1", order="ASC")
    assert [entry["input"] for entry in oldest_first] == ["Question 1", "Question 2"]


def test_agent_get_history_rejects_invalid_order(agent_module):
    agent = agent_module.Agent()
    with pytest.raises(ValueError):
        agent.get_history(user_id="user-1", session_id="session-1", order="invalid")
