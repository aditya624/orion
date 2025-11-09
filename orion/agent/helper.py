from langfuse import Langfuse
from orion.config import Settings
import pytz, datetime

from pydantic import BaseModel, Field
from typing import Annotated, Optional
from langgraph.graph.message import add_messages, AnyMessage
from typing_extensions import TypedDict

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    extra_callbacks: Optional[list]


def get_args_schema(prompt):
    class KnowledgeTools(BaseModel):
        query: str = Field(
            description=prompt["knowledge"]["config"]["desc_schema"]["query"]
        )

    schema = {
        "knowledge": KnowledgeTools
    }

    return schema

def get_timezone():
    timezone = pytz.timezone('Asia/Jakarta')
    return timezone

def get_time_area(timezone):
    return datetime.datetime.now(timezone)

def get_date_and_time():
    timezone = get_timezone()
    times_area = get_time_area(timezone)
    format_date = "%Y-%m-%d %H:%M:%S"
    return times_area.strftime(format_date)

def load_prompt(settings: Settings, langfuse: Langfuse):
    system_prompt_loader = langfuse.get_prompt(
        name=settings.langfuse.system_prompt_name,
        version=settings.langfuse.system_prompt_version
    )

    knowledge_loader = langfuse.get_prompt(
        name=settings.langfuse.knowledge_prompt_name,
        version=settings.langfuse.knowledge_prompt_version
    )

    chain_prompt_loader = langfuse.get_prompt(
        name=settings.langfuse.summary_prompt_name,
        version=settings.langfuse.summary_prompt_version
    )

    prompt = {
        "agent": {
            "langfuse_prompt": system_prompt_loader,
            "prompt": system_prompt_loader.get_langchain_prompt(),
            "config": system_prompt_loader.config
        },
        "knowledge": {
            "langfuse_prompt": knowledge_loader,
            "description": knowledge_loader.get_langchain_prompt(),
            "config": knowledge_loader.config
        },
        "chain": {
            "langfuse_prompt": chain_prompt_loader,
            "prompt": chain_prompt_loader.get_langchain_prompt(),
            "config": chain_prompt_loader.config
        }
    }

    return prompt