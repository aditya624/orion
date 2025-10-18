from langchain_groq import ChatGroq
from orion.config import settings
from orion.agent.helper import load_prompt, get_date_and_time, State

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad.tools import (
    format_to_tool_messages,
)
from langchain.agents import AgentExecutor
from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition


class Agent(object):
    def __init__(self):
        self.model = ChatGroq(
            model=settings.groq.model,
            api_key=settings.groq.api_key
        )

        self.memory = MongoDBChatMessageHistory(
            session_id="default", 
            connection_string=settings.mongodb.uri,
            database_name=settings.mongodb.database,
            collection_name=settings.mongodb.collection,
            history_key="history"
        )
        self.langfuse = Langfuse()
        self.prompt = load_prompt(settings, self.langfuse)
        self.model = ChatGroq(
            model=self.prompt["agent"]["config"]["model"],
            api_key=settings.groq.api_key
        )
        self.bindtools, self.tools = self.get_tools()

        # self.agent = self.agent_builder()
        self.graph = self.graph_builder()

    def get_tools(self):
        tools = {}

        bindtools = [
        ]

        return bindtools, tools

    def get_memory(self, session_id):
        return MongoDBChatMessageHistory(
            session_id=session_id, 
            connection_string=settings.mongodb.uri,
            database_name=settings.mongodb.database,
            collection_name=settings.mongodb.collection,
            history_size=settings.mongodb.history_size
        )

    def graph_builder(self):
        def chatbot(state: State):
            messages = state["messages"]
            extra_callbacks = state.get("extra_callbacks", [])
            current_date = get_date_and_time()

            system_prompt = self.prompt["agent"]["prompt"].format(current_date=current_date)

            memory = self.get_memory(session_id=state["session_id"])

            inputs = [SystemMessage(content=system_prompt)] + memory.messages + messages

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

    def agent_builder(self):
        llm_with_tools = self.model.bind_tools(self.bindtools)
        agent_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    self.prompt["agent"]["prompt"],
                ),
                # MessagesPlaceholder(variable_name="history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        pipeline = {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_tool_messages(
                x["intermediate_steps"]
            ),
            "current_date": lambda x: get_date_and_time(),
        }

        # pipeline_with_history = RunnableWithMessageHistory(
        #     pipeline,
        #     lambda session_id: MongoDBChatMessageHistory(
        #         session_id=session_id,
        #         connection_string=settings.mongodb.uri,
        #         database_name=settings.mongodb.database,
        #         collection_name=settings.mongodb.collection,
        #     ),
        #     input_messages_key="input",
        #     history_messages_key="history",
        # )

        agent = (
            pipeline
            | agent_prompt
            | llm_with_tools
            | ToolsAgentOutputParser()
        )

        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.bindtools,
            verbose=False,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            max_iterations=settings.groq.max_iterations,
            stream_runnable=False,
        )

        return agent_executor

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

        memory = self.get_memory(session_id=session_id)
        memory.add_user_message(input)
        memory.add_ai_message(answer)

        return answer