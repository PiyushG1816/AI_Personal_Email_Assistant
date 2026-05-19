from langchain_google_genai import ChatGoogleGenerativeAI 
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.graph import MessagesState, StateGraph, START, END
from langchain_google_community.calendar.create_event import CalendarCreateEvent
from langchain_google_community.calendar.delete_event import CalendarDeleteEvent
from langchain_google_community.calendar.move_event import CalendarMoveEvent
from langchain_google_community.calendar.search_events import CalendarSearchEvents
from langchain_google_community.calendar.update_event import CalendarUpdateEvent
from typing import Literal
import tzlocal

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# Tools setup
tools = [
    CalendarSearchEvents(),
    CalendarCreateEvent(),
    CalendarDeleteEvent(),
    CalendarMoveEvent(),
    CalendarUpdateEvent()
]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = model.bind_tools(tools)
user_tz = str(tzlocal.get_localzone())

# Nodes
def llm_call(state: MessagesState):
    system = SystemMessage(content=f"""You are a smart calendar assistant.
User timezone: {user_tz}

When scheduling a meeting:
1. First LIST events in that time window to check for conflicts
2. If conflict exists — clearly show the conflict details and ask user what to do:
   - Delete conflicting meeting and schedule new one
   - Move conflicting meeting to another time
   - Move new meeting to another time
   - Cancel entirely
3. Execute the chosen action
4. Confirm final calendar state

Always use timezone: {user_tz}""")
    
    return {
        "messages": [llm_with_tools.invoke([system] + state["messages"])]
    }

def tool_node(state: MessagesState):
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(
            content=str(observation),
            tool_call_id=tool_call["id"]
        ))
    return {"messages": result}

def should_continue(state: MessagesState) -> Literal["tool_node", "human_input", "__end__"]:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tool_node"
    # If agent is asking a question, get human input
    if "?" in last_message.content:
        return "human_input"
    return END

def human_input_node(state: MessagesState):
    last_message = state["messages"][-1]
    print("\n=== CALENDAR AGENT ===")
    print(last_message.content)
    user_response = input("\nYour response: ").strip()
    return {"messages": [HumanMessage(content=user_response)]}

# Build graph
agent_builder = StateGraph(MessagesState)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)
agent_builder.add_node("human_input", human_input_node)

agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", "human_input", END]
)
agent_builder.add_edge("tool_node", "llm_call")
agent_builder.add_edge("human_input", "llm_call")

calendar_agent = agent_builder.compile()


# Calendar node for your main graph
def calendar_node(state: dict) -> dict:
    extracted = state["extracted"]
    
    query = f"""Schedule this meeting:
- Title: {extracted.meeting_title}
- Date: {extracted.meeting_date}
- Time: {extracted.meeting_time}  
- Duration: {extracted.meeting_duration_minutes or 60} minutes
- Timezone: {user_tz}

First check for conflicts in this time window."""

    result = calendar_agent.invoke({
        "messages": [HumanMessage(content=query)]
    })
    
    print("\n=== FINAL RESULT ===")
    print(result["messages"][-1].content)

    return state
