from typing import (
    Annotated, # Provides additional context without affecting the type itself 
    Sequence, # To automatically handle the state updates for sequences such as adding new messages to a chat history
    TypedDict
)
from dotenv import load_dotenv
from langchain_core.messages import (
    BaseMessage, # The foundational class for all messages types in LangGraph
    ToolMessage, # Passes data back to LLM after it calls a tool such as the content and the tool_call_id
    SystemMessage, # Message for providing instructions to the LLM
)
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import (
    add_messages # Reducer function
    # Rule that controls how updates from nodes are combined with the existing state
    # Tells us how to merge new data into the current state
    # Without a reducer, updates would have replaced the existing value entirely
) 
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

@tool
def add(a: int, b: int):
    """This is an addition function that adds 2 numbers together"""

    return a + b

@tool
def subtract(a: int, b: int):
    """This is an subtraction function that subtracts 2 numbers together"""

    return a - b

@tool
def multiply(a: int, b: int):
    """This is an multiplication function that multiplies 2 numbers together"""

    return a * b

tools = [add, subtract, multiply]

model = ChatOpenAI(model='gpt-4o').bind_tools(tools)

def model_call(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(
        content='You are my AI assistant, please answer my query to the best of your ability')

    response = model.invoke([system_prompt] + list(state['messages']))
    
    return {'messages': [response]}

def should_continue(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    if not last_message.tool_calls:
        return 'end'
    else: 
        return 'continue'
    
graph = StateGraph(AgentState)
graph.add_node('our_agent', model_call)

tools_node = ToolNode(tools=tools)
graph.add_node('tools', tools_node)

graph.add_edge(START, 'our_agent')

graph.add_conditional_edges(
    'our_agent',
    should_continue,
    {
        'continue': 'tools',
        'end': END
    }
)

graph.add_edge('tools', 'our_agent')

app = graph.compile()

def print_stream(stream):
    for s in stream:
        message = s['messages'][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()

inputs = {
    'messages': [
        ('user', 'Add 40 + 12 and then multiply the result by 6. Also tell me a joke please')
    ]
}

print_stream(app.stream(inputs, stream_mode='values'))