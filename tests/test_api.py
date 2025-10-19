import types
import sys
import importlib
import asyncio

import pytest
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import status, HTTPException


@pytest.fixture
def stub_settings(monkeypatch):
    settings = types.SimpleNamespace(
        app_name="Test App",
        version="0.1.0",
        token="test-token",
        groq=types.SimpleNamespace(api_key="fake-key"),
        mongodb=types.SimpleNamespace(
            uri="mongodb://localhost",
            database="test_db",
            collection="chat_history",
            history_size=5,
        ),
        langfuse=types.SimpleNamespace(
            system_prompt_name="agent",
            system_prompt_version=None,
            knowledge_prompt_name="knowledge",
            knowledge_prompt_version=None,
        ),
    )
    monkeypatch.setattr("orion.api.v1.auth.settings", settings, raising=False)
    return settings


@pytest.fixture
def api_client(monkeypatch, stub_settings):
    class FakeAgent:
        def __init__(self):
            self.calls = []

        def generate(self, input, session_id, extra_callbacks=None):
            self.calls.append((input, session_id))
            return f"answer for {input}"

    class FakeKnowledge:
        def __init__(self):
            self.upload_calls = []

        def upload_link(self, links):
            self.upload_calls.append(list(links))
            return {
                "exists": links[:1],
                "not_exists": links[1:],
            }

    modules_to_clear = [
        "orion.api.v1.agent.routes",
        "orion.api.v1.knowledge.routes",
        "orion.main",
    ]
    for name in modules_to_clear:
        sys.modules.pop(name, None)

    monkeypatch.setattr("orion.agent.agent.settings", stub_settings, raising=False)
    monkeypatch.setattr("orion.agent.agent.Agent", FakeAgent)
    monkeypatch.setattr("orion.tools.knowledge.Knowledge", FakeKnowledge)
    monkeypatch.setattr("orion.main.settings", stub_settings, raising=False)

    agent_routes = importlib.import_module("orion.api.v1.agent.routes")
    knowledge_routes = importlib.import_module("orion.api.v1.knowledge.routes")

    monkeypatch.setattr(agent_routes, "_agent", FakeAgent())
    monkeypatch.setattr(knowledge_routes, "_knowledge", FakeKnowledge())

    main = importlib.import_module("orion.main")
    client = TestClient(main.app)
    return client, agent_routes._agent, knowledge_routes._knowledge


def test_root_endpoint(api_client):
    client, _, _ = api_client
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Welcome to Orion Agent API"


def test_agent_generate_endpoint(api_client, stub_settings):
    client, agent, _ = api_client
    headers = {"Authorization": f"Bearer {stub_settings.token}"}
    payload = {"input": "hello", "session_id": "abc"}

    response = client.post("/v1/agent/generate", json=payload, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["answer"] == "answer for hello"
    assert agent.calls[-1] == ("hello", "abc")


def test_agent_generate_requires_token(api_client):
    client, _, _ = api_client
    response = client.post("/v1/agent/generate", json={"input": "hi", "session_id": "s"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_knowledge_upload_link(api_client, stub_settings):
    client, _, knowledge = api_client
    headers = {"Authorization": f"Bearer {stub_settings.token}"}
    payload = {"links": ["https://example.com/a", "https://example.com/a", "https://example.com/b"]}

    response = client.post("/v1/knowledge/upload-link", json=payload, headers=headers)

    assert response.status_code == status.HTTP_200_OK
    assert knowledge.upload_calls[-1] == [
        "https://example.com/a",
        "https://example.com/b",
    ]
    body = response.json()
    assert body["skipped"] == ["https://example.com/a"]
    assert body["processed"] == ["https://example.com/b"]
    assert body["counts"] == {
        "skipped": 1,
        "processed": 1,
        "total_input": 3,
        "total_unique": 2,
    }


def test_health_endpoints(api_client, stub_settings):
    client, _, _ = api_client
    headers = {"Authorization": f"Bearer {stub_settings.token}"}

    agent_health = client.get("/v1/agent/health", headers=headers)
    knowledge_health = client.get("/v1/knowledge/health", headers=headers)

    assert agent_health.status_code == status.HTTP_200_OK
    assert knowledge_health.status_code == status.HTTP_200_OK


def test_verify_token_success(stub_settings):
    from orion.api.v1 import auth

    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=stub_settings.token)
    token = asyncio.run(auth.verify_token(credentials))
    assert token == stub_settings.token


def test_verify_token_missing_credentials(stub_settings):
    from orion.api.v1 import auth
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.verify_token(None))
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Missing" in exc.value.detail


def test_verify_token_invalid_token(stub_settings):
    from orion.api.v1 import auth
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(auth.verify_token(credentials))
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid" in exc.value.detail
