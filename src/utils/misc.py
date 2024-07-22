from langchain_core.messages import ToolMessage, AIMessage
from langchain_core.runnables import RunnableLambda
from langgraph.prebuilt import ToolNode as BaseToolNode
from flask_socketio import SocketIO
from typing import List, Union, Dict, Any

def create_tool_node_with_fallback(tools: list) -> dict:
    return BaseToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )

def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n please fix your mistakes. \n Full State: {state}",
                # content="Continue",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def _print_event(event: dict, _printed: set, max_length=1500):
    current_state = event.get("dialog_state")
    if current_state:
        print("Currently in: ", current_state[-1])
    message = event.get("messages")
    if message:
        if isinstance(message, list):
            message = message[-1]
        if message.id not in _printed:
            msg_repr = message.pretty_repr(html=True)
            if len(msg_repr) > max_length:
                msg_repr = msg_repr[:max_length] + " ... (truncated)"
            print(msg_repr)
            _printed.add(message.id)

# def process_message(graph, state, config, _printed):
#     global conversation_state
#     events = part_1_graph.stream(state, config, stream_mode="values")
    
#     for event in events:
#         message = event.get("messages")
#         if message:
#             if isinstance(message, list):
#                 message = message[-1]
#             if message.id not in _printed:
#                 if isinstance(message, AIMessage):
#                     socketio.emit('bot_response', {'message': message.content})
#                     if message.tool_calls:
#                         for tool_call in message.tool_calls:
#                             tool_name = tool_call["name"]
#                             tool_call_id = tool_call["id"]
#                             if tool_name in ["AskContactPermissionTool", "AskCreditPullPermissionTool"]:
#                                 question = "Do you give permission for us to contact you through email or phone number provided? (Please type: yes/y/no/n)" if tool_name == "AskContactPermissionTool" else "Do you give permission for us to pull your credit? This will NOT affect your credit score. (Please type: yes/y/no/n)"
#                                 latest_tool_call = {
#                                     'tool_name': tool_name,
#                                     'tool_call_id': tool_call_id,
#                                     'message': question
#                                 }
#                                 socketio.emit('user_input_required', latest_tool_call)

#         _print_event(event, _printed)

    # conversation_state["messages"].append(message)