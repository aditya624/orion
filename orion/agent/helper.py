from langfuse import Langfuse
from orion.config import Settings
import pytz, datetime

from typing import Annotated, Optional
from langgraph.graph.message import add_messages, AnyMessage
from typing_extensions import TypedDict

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    extra_callbacks: Optional[list]


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
    system_prompt_loder = langfuse.get_prompt(
        name=settings.langfuse.system_prompt_name,
        version=settings.langfuse.system_prompt_version
    )

    prompt = {
        "agent": {
            "prompt": system_prompt_loder.get_langchain_prompt(),
            "config": system_prompt_loder.config
        }
    }

    return prompt