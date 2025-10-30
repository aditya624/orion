import re
from langchain_groq import ChatGroq
from orion.config import settings
from orion.agent.helper import load_prompt, get_date_and_time, State, get_args_schema
from orion.tools.knowledge import Knowledge
from orion.agent.history import HistoryStore

from langchain.tools import StructuredTool

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition


class Agent(object):
    def __init__(self):
        self.langfuse = Langfuse()
        self.prompt = load_prompt(settings, self.langfuse)

        self.model = ChatGroq(
            model=self.prompt["agent"]["config"]["model"],
            api_key=settings.groq.api_key
        )

        self.knowledge = Knowledge(prompt=self.prompt)
        self.bindtools = self.get_tools()

        self.graph = self.graph_builder()
        self.history_store = HistoryStore()

    def get_tools(self):
        args_schema = get_args_schema(self.prompt)
        bindtools = [
            StructuredTool.from_function(
                func=self.knowledge.query,
                args_schema=args_schema["knowledge"],
                name=self.prompt["knowledge"]["config"]["name"],
                description=self.prompt["knowledge"]["description"]
            ),
        ]

        return bindtools

    def graph_builder(self):
        def chatbot(state: State):
            messages = state["messages"]
            extra_callbacks = state.get("extra_callbacks", [])

            response = llm_with_tools.invoke(
                messages,
                config={
                    "callbacks": [CallbackHandler()]
                    + extra_callbacks
                },
            )

            return {"messages": [response]}

        llm_with_tools = self.model.bind_tools(self.bindtools)
        graph_builder = StateGraph(State)

        tool_node = ToolNode(tools=self.bindtools)
        graph_builder.add_node("tools", tool_node)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_node("chatbot", chatbot)

        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")
        graph_builder.set_entry_point("chatbot")
        graph = graph_builder.compile().with_config({"run_name": "agent"})

        return graph

    def get_history(self, user_id, session_id, order="DESC", offset=0, limit=20):
        return self.history_store.list(
            user_id=user_id,
            session_id=session_id,
            order=order,
            offset=offset,
            limit=limit,
        )

    def generate(self, input, session_id, user_id, extra_callbacks=[]):

        history_message_user = self.history_store.get_history_for_messages(
            user_id=user_id,
            session_id=session_id,
            size=settings.mongodb.history_size
        )

        answer = self.graph.invoke(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": self.prompt["agent"]["prompt"].format(current_date=get_date_and_time()),
                    },
                ] 
                + history_message_user
                + [
                    {
                        "role": "user",
                        "content": input,
                    },
                ]
            },
            {
                "callbacks": [CallbackHandler()] 
                + extra_callbacks,
            },
        )["messages"][-1].content

        answer = re.sub(r"<think>.*?</think>", "", answer.strip(), flags=re.DOTALL)
        self.history_store.save(user_id=user_id, session_id=session_id, input_text=input, answer=answer)

        return answer
