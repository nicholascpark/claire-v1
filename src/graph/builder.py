from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from src.state import ConvoState
from src.agents.assistant import Assistant
from src.tools.api_tools import credit_pull_api_tool, lead_create_api_tool
from src.tools.permission_tools import ask_contact_permission_tool, ask_credit_pull_permission_tool
from src.tools.savings_estimate_tool import savings_estimate_tool
from src.utils.handle_convo import update_convo_state
from src.utils.misc import create_tool_node_with_fallback
from src.prompts import primary_assistant_prompt
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import tools_condition
# from langchain_openai import ChatOpenAI
from src.utils.mssql_saver import MSSQLSaver
from src.config import llm
import pyodbc
import os
from dotenv import load_dotenv
load_dotenv()

# llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature = 0, max_tokens = 1000)

permission_tools = [ask_contact_permission_tool, ask_credit_pull_permission_tool]
permission_tool_node = create_tool_node_with_fallback(permission_tools)

savings_estimate_tools = [savings_estimate_tool]
savings_estimate_tool_node = create_tool_node_with_fallback(savings_estimate_tools)

api_tools = [lead_create_api_tool, credit_pull_api_tool]#, math_tool]
api_tool_node = create_tool_node_with_fallback(api_tools)

all_tools = savings_estimate_tools + api_tools + permission_tools 
primary_assistant_chain = primary_assistant_prompt | llm.bind_tools(all_tools)# + savings_estimate_tool)

def create_graph():

    builder = StateGraph(ConvoState)

    builder.add_node("assistant", Assistant(primary_assistant_chain))
    builder.set_entry_point("assistant")

    builder.add_node("tools", create_tool_node_with_fallback(all_tools))
    # builder.add_node("permission_tools", permission_tool_node)
    # builder.add_node("savings_estimate_tools", savings_estimate_tool_node)
    builder.add_node("update_convo_state", update_convo_state)

    builder.add_conditional_edges(
        "assistant",
        tools_condition,
        {
            "tools": "tools",
            "__end__": END,
        }
    )
    builder.add_edge("tools", "update_convo_state")
    builder.add_edge("update_convo_state", "assistant")

    conn_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={os.getenv("SQL_SERVER")};"
        f"DATABASE={os.getenv("SQL_DATABASE")};"
        f"UID={os.getenv("SQL_USERNAME")};"
        f"PWD={os.getenv("SQL_PWD")};"
    )
    # memory = MSSQLSaver(conn_string)
    memory = MemorySaver()

    return builder.compile(checkpointer=memory,)# interrupt_after=["api_tools"]    )

if __name__ == "__main__":
    part_1_graph = create_graph()
    # from IPython.display import Image, display
    # display(Image(part_1_graph.get_graph(xray=True).draw_mermaid_png()))