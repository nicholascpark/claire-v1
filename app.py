from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import uuid
from src.state import ConvoState, RequiredInformation
from src.graph.builder import create_graph
from src.utils.misc import _print_event
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from queue import Queue
from threading import Thread
from typing import Dict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

part_1_graph = create_graph()

# Global variables for thread_id and config
thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        "thread_id": thread_id,
    }
}

_printed = set()

# Global variable to store the conversation state
conversation_state = None

# Message queue and processing flag
message_queue = Queue()
processing = False

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    global conversation_state
    print('Client connected')
    initial_message = generate_initial_message()
    conversation_state = ConvoState(
        user_input="",
        messages=[AIMessage(content=initial_message)],
    )
    emit('bot_response', {'message': initial_message})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('user_message')
def handle_message(message):
    global conversation_state
    conversation_state["user_input"] = message
    conversation_state["messages"].append(HumanMessage(content=message))
    process_message(conversation_state)
    # message_queue.put(("user_message", conversation_state))
    # process_queue()

def check_required_info(state) -> bool:
    required_info = state.get("required_information", {})
    return all(required_info.get(field) is not None for field in required_info)

def handle_contact_permission(response: str) -> Dict[str, bool]:
    if not check_required_info(conversation_state):
        return {"message": "Collect the list of required information first."}
    
    if conversation_state.get("contact_permission") is not None:
        return {"message": "Contact permission already obtained. Move on to the next tool."}
    
    if response in ['y', 'yes']:
        return {"contact_permission": True}
    elif response in ['n', 'no']:
        return {"contact_permission": False, "message": "User has not given permission to be contacted. We cannot proceed without the contact permission."}
    else:
        return {"message": "Invalid input. Please answer with 'yes/y' or 'no/n'."}

def handle_credit_pull_permission(response: str) -> Dict[str, bool]:
    if not check_required_info(conversation_state):
        return {"message": "Collect the list of required information first."}
    
    if not conversation_state.get("contact_permission"):
        return {"message": "Obtain the contact permission first."}
    
    if conversation_state.get("credit_pull_permission") is not None:
        return {"message": "Credit pull permission already obtained. Move on to the next tool."}

    if response in ['y', 'yes']:
        return {"credit_pull_permission": True}
    elif response in ['n', 'no']:
        return {"credit_pull_permission": False}
    else:
        return {"message": "Invalid input. Please answer with 'yes/y' or 'no/n'."}

@socketio.on('user_input_response')
def handle_user_input_response(data):
    global conversation_state
    tool_name = data['tool_name']
    user_response = data['response'].lower()
    tool_call_id = data['tool_call_id']
    
    if tool_name == "AskContactPermissionTool":
        result = handle_contact_permission(user_response)
    elif tool_name == "AskCreditPullPermissionTool":
        result = handle_credit_pull_permission(user_response)
    else:
        emit('bot_response', {'message': "Unknown tool called."})
        return

    if result.get("message"):
        emit('bot_response', {'message': result["message"]})
        return
    # Create a ToolMessage with the user's response
    tool_message = ToolMessage(content=str(result), tool_call_id=tool_call_id)
    
    # Update the conversation state with the user's response
    conversation_state["user_input"] = user_response
    conversation_state["messages"].append(tool_message)
    conversation_state.update(result)
    
    # message_queue.put(("tool_response", conversation_state))
    # process_queue()
    process_message(conversation_state)

# def process_queue():
#     global processing
#     if processing:
#         return
    
#     processing = True
#     Thread(target=process_messages).start()

# def process_messages():
#     global processing, conversation_state
#     while not message_queue.empty():
#         message_type, state = message_queue.get()
#         process_message(state)
    
#     processing = False

def process_message(state):
    global conversation_state
    events = part_1_graph.stream(state, config, stream_mode="values")
    
    for event in events:
        message = event.get("messages")
        if message:
            if isinstance(message, list):
                message = message[-1]
            if message.id not in _printed:
                if isinstance(message, AIMessage):
                    socketio.emit('bot_response', {'message': message.content})
                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_name = tool_call["name"]
                            tool_call_id = tool_call["id"]
                            if tool_name in ["AskContactPermissionTool", "AskCreditPullPermissionTool"]:
                                question = "Do you give permission for us to contact you through email or phone number provided? (Please type: yes/y/no/n)" if tool_name == "AskContactPermissionTool" else "Do you give permission for us to pull your credit? This will NOT affect your credit score. (Please type: yes/y/no/n)"
                                latest_tool_call = {
                                    'tool_name': tool_name,
                                    'tool_call_id': tool_call_id,
                                    'message': question
                                }
                                socketio.emit('user_input_required', latest_tool_call)

        _print_event(event, _printed)

    conversation_state["messages"].append(message)

def generate_initial_message():
    initial_state = ConvoState(
        user_input=".",
        messages=[HumanMessage(content=".")],
    )
    events = part_1_graph.stream(initial_state, config, stream_mode="values")
    
    for event in events:
        if 'messages' in event:
            for msg in event['messages']:
                if isinstance(msg, AIMessage):
                    return msg.content
    
    return "Hello! I'm Claire, a debt resolution specialist at ClearOne Advantage. How can I assist you today?"

if __name__ == '__main__':
    socketio.run(app, debug=True)