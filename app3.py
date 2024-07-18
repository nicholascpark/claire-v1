from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import uuid
from src.state import ConvoState, RequiredInformation
from src.graph.builder import create_graph
from src.utils.misc import _print_event
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.utils.handle_convo import handle_contact_permission, handle_credit_pull_permission
from src.utils.info_collector import check_all_required_info
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
socketio = SocketIO(app, cors_allowed_origins="*")

part_1_graph = create_graph()

thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        "thread_id": thread_id,
    }
}

_printed = set()

conversation_state = None

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


@socketio.on('user_input_response')
def handle_user_input_response(data):
    global conversation_state
    tool_name = data['tool_name']
    user_response = data['response'].lower()
    tool_call_id = data['tool_call_id']
    
    if tool_name == "AskContactPermissionTool":
        result = handle_contact_permission(conversation_state, user_response)
    elif tool_name == "AskCreditPullPermissionTool":
        result = handle_credit_pull_permission(conversation_state, user_response)
    else:
        emit('bot_response', {'message': "Unknown tool called."})
        return

    if result.get("message"):
        emit('user_input_required', {
            'tool_name': tool_name,
            'tool_call_id': tool_call_id,
            'message': result["message"]
        })
        return
    
    # Create a ToolMessage with the user's response
    tool_message = ToolMessage(content=str(result), tool_call_id=tool_call_id)
    
    # Update the conversation state with the user's response
    conversation_state["user_input"] = user_response
    conversation_state["messages"].append(tool_message)
    conversation_state.update(result)
    process_message(conversation_state)

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
                    if len(message.content.strip()) > 0:
                        socketio.emit('bot_response', {'message': message.content})
                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_name = tool_call["name"]
                            tool_call_id = tool_call["id"]
                            if tool_name in ["AskContactPermissionTool", "AskCreditPullPermissionTool"]:
                                question = "Do you give permission for us to contact you through email or phone number provided?* (Please type: yes/y/no/n)" if tool_name == "AskContactPermissionTool" else "Do you give permission for us to pull your credit? This will NOT affect your credit score.** (Please type: yes/y/no/n)"
                                latest_tool_call = {
                                    'tool_name': tool_name,
                                    'tool_call_id': tool_call_id,
                                    'message': question
                                }
                                socketio.emit('user_input_required', latest_tool_call)

        # _print_event(event, _printed)

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
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port)