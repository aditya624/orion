from langchain_groq import ChatGroq
from orion.config import settings
from orion.agent.helper import load_prompt, get_date_and_time, State, get_args_schema
from orion.tools.knowledge import Knowledge

from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain.tools import StructuredTool

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from langchain_core.messages import SystemMessage
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

        self.knowledge = Knowledge()
        self.bindtools = self.get_tools()

        self.graph = self.graph_builder()

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

    def get_memory(self, session_id, history_size):

        if history_size == -1:
            history_size = settings.mongodb.history_size

        return MongoDBChatMessageHistory(
            session_id=session_id, 
            connection_string=settings.mongodb.uri,
            database_name=settings.mongodb.database,
            collection_name=settings.mongodb.collection,
            history_size=history_size
        )

    def graph_builder(self):
        def chatbot(state: State):
            messages = state["messages"]
            extra_callbacks = state.get("extra_callbacks", [])
            current_date = get_date_and_time()

            system_prompt = self.prompt["agent"]["prompt"].format(current_date=current_date)

            memory = self.get_memory(session_id=state["session_id"], history_size=-1)

            system_prompt = SystemMessage(content=system_prompt)
            inputs = [system_prompt] + memory.messages + messages

            response = llm_with_tools.invoke(
                inputs,
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
        graph = graph_builder.compile()

        return graph

    def generate(self, input, session_id, extra_callbacks=[]):
        answer = self.graph.invoke(
            {
                "messages": [("human", input)],
                "session_id": session_id,
            },
            {
                "callbacks": [CallbackHandler()]
                + extra_callbacks,
            },
        )["messages"][-1].content

        memory = self.get_memory(session_id=session_id, history_size=-1)
        memory.add_user_message(input)
        memory.add_ai_message(answer)
        return answer