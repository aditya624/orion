import re
from langchain_groq import ChatGroq
from orion.config import settings
from orion.agent.helper import load_prompt, get_date_and_time, State, get_args_schema
from orion.tools.knowledge import Knowledge
from orion.agent.history import HistoryStore

from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain_mcp_adapters.tools import load_mcp_tools

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from langchain.agents import create_agent
# from langgraph.graph import StateGraph, START
# from langgraph.prebuilt import ToolNode, tools_condition


class Agent(object):
    def __init__(self):
        self.langfuse = Langfuse()
        self.prompt = load_prompt(settings, self.langfuse)

        self.model = ChatGroq(
            model=self.prompt["agent"]["config"]["model"],
            api_key=settings.groq.api_key
        )

        self.knowledge = Knowledge(prompt=self.prompt)

        self.graph = None
        self.history_store = HistoryStore()

    def get_mcp(self):
        client = MultiServerMCPClient(  
            {
                "knowledge": {
                    "transport": "streamable_http",  # HTTP-based remote server
                    # Ensure you start your weather server on port 8000
                    "url": "http://localhost:8181/mcp",
                }
            }
        )

        return client

    async def graph_builder(self):
        mcp_client = self.get_mcp()
        tools = await mcp_client.get_tools()
        graph = create_agent(
            model=self.model,
            tools=tools,
        )
        return graph

    async def get_graph(self):
        if self.graph is None:
            self.graph = await self.graph_builder()
        return self.graph

    def get_history(self, user_id, session_id, order="DESC", offset=0, limit=20):
        return self.history_store.list(
            user_id=user_id,
            session_id=session_id,
            order=order,
            offset=offset,
            limit=limit,
        )

    async def generate(self, input, session_id, user_id, extra_callbacks=[]):
        history_message_user = self.history_store.get_history_for_messages(
            user_id=user_id,
            session_id=session_id,
            size=settings.mongodb.history_size,
        )

        graph = await self.get_graph()  # pastikan ini bukan coroutine yang belum di-await

        # 1) TUNGGU hasil ainvoke dulu
        result = await graph.ainvoke(
            {
                "messages": (
                    [
                        {
                            "role": "system",
                            "content": self.prompt["agent"]["prompt"].format(
                                current_date=get_date_and_time()
                            ),
                        }
                    ]
                    + history_message_user
                    + [{"role": "user", "content": input}]
                )
            },
            {"callbacks": [CallbackHandler()] + extra_callbacks},
        )

        # 2) Baru ekstrak konten (tanpa indexing sebelum await)
        if isinstance(result, dict):
            if "messages" in result and result["messages"]:
                content = result["messages"][-1].content
            elif "output" in result:
                content = result["output"]
            else:
                content = str(result)
        elif hasattr(result, "content"):
            content = result.content
        else:
            content = str(result)

        answer_text = re.sub(r"<think>.*?</think>", "", content.strip(), flags=re.DOTALL)
        self.history_store.save(user_id=user_id, session_id=session_id, input_text=input, answer=answer_text)
        return answer_text
