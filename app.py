from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import uuid
from src.state import ConvoState, RequiredInformation
from src.graph.builder import create_graph
from src.utils.misc import _print_event
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from src.utils.handle_convo import handle_contact_permission, handle_credit_pull_permission
from src.utils.info_collector import check_all_required_info
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
socketio = SocketIO(app, manage_session=False)

part_1_graph = create_graph()
_printed = set()
session_store = {}

def serialize_message(msg):
    serialized = {
        'type': msg.__class__.__name__,
    }
    for key, value in msg.__dict__.items():
        if isinstance(value, (str, int, float, bool, list, dict, type(None))):
            serialized[key] = value
    return serialized

def deserialize_message(msg_dict):
    msg_type = msg_dict.pop('type')
    message_classes = {
        'human': HumanMessage,
        'ai': AIMessage,
        'tool': ToolMessage,
        'system': SystemMessage
    }
    
    if msg_type not in message_classes:
        raise ValueError(f"Unknown message type: {msg_type}")
    
    # Create the message object with all the attributes in msg_dict
    return message_classes[msg_type](**msg_dict)


def serialize_convo_state(state):
    return json.dumps({
        'user_input': state['user_input'],
        'messages': [serialize_message(msg) for msg in state['messages']],
        'required_information': state['required_information'].__dict__,
        'contact_permission': state['contact_permission'],
        'credit_pull_permission': state['credit_pull_permission'],
        'credit_pull_complete': state['credit_pull_complete'],
        'lead_create_complete': state['lead_create_complete'],
        'savings_estimate': state['savings_estimate'],
        'reason_for_decline': state['reason_for_decline']
    })

def deserialize_convo_state(state_json):
    state_dict = json.loads(state_json)
    return ConvoState(
        user_input=state_dict['user_input'],
        messages=[deserialize_message(msg) for msg in state_dict['messages']],
        required_information=RequiredInformation(**state_dict['required_information']),
        contact_permission=state_dict['contact_permission'],
        credit_pull_permission=state_dict['credit_pull_permission'],
        credit_pull_complete=state_dict['credit_pull_complete'],
        lead_create_complete=state_dict['lead_create_complete'],
        savings_estimate=state_dict['savings_estimate'],
        reason_for_decline=state_dict['reason_for_decline']
    )


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    print('Client connected')
    session_id = request.sid
    join_room(session_id)
    thread_id = str(uuid.uuid4())
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    initial_message = generate_initial_message(config)
    initial_state = ConvoState(
        user_input="",
        messages=[AIMessage(content=initial_message)],
        required_information=RequiredInformation(),
        contact_permission=None,
        credit_pull_permission=None,
        credit_pull_complete=None,
        lead_create_complete=None,
        savings_estimate=None,
        reason_for_decline=None
    )
    session_store[session_id] = {
        'state': serialize_convo_state(initial_state),
        'config': config
    }
    print(f"Session {session_id} initialized with thread_id: {thread_id}")
    emit('bot_response', {'message': initial_message}, room=session_id)


@socketio.on('disconnect')
def handle_disconnect():
    session_id = request.sid
    print(f'Client disconnected: {session_id}')
    leave_room(session_id)
    if session_id in session_store:
        del session_store[session_id]
        print(f"Session {session_id} removed")

@socketio.on('user_message')
def handle_message(message):
    session_id = request.sid
    print(f"Received message from {session_id}: {message}")
    if session_id not in session_store:
        print(f"Session {session_id} not found")
        emit('bot_response', {'message': "Session expired. Please refresh the page."}, room=session_id)
        return
    
    try:
        conversation_state = deserialize_convo_state(session_store[session_id]['state'])
        config = session_store[session_id]['config']
        conversation_state['user_input'] = message
        conversation_state['messages'].append(HumanMessage(content=message))
        updated_state = process_message(conversation_state, session_id, config)
        session_store[session_id]['state'] = serialize_convo_state(updated_state)
        print(f"Updated session {session_id} with new state")
    except Exception as e:
        print(f"Error processing message: {str(e)}")
        emit('bot_response', {'message': "An error occurred. Please try again."}, room=session_id)

@socketio.on('user_input_response')
def handle_user_input_response(data):
    session_id = request.sid
    if session_id not in session_store:
        emit('bot_response', {'message': "Session expired. Please refresh the page."}, room=session_id)
        return
    
    print("DATA:\n", data)

    conversation_state = deserialize_convo_state(session_store[session_id]['state'])
    config = session_store[session_id]['config']
    tool_name = data['tool_name']
    user_response = data['response'].lower()
    tool_call_id = data['tool_call_id']
    
    if tool_name == "AskContactPermissionTool":
        result = handle_contact_permission(conversation_state, user_response)
    elif tool_name == "AskCreditPullPermissionTool":
        result = handle_credit_pull_permission(conversation_state, user_response)
    else:
        emit('bot_response', {'message': "Unknown tool called."}, room=session_id)
        session_store[session_id]['state'] = serialize_convo_state(conversation_state)
        return

    if result.get("message"):
        conversation_state["messages"].append(AIMessage(content=result["message"], tool_call_id=tool_call_id))
        emit('user_input_required', {
            'tool_name': tool_name,
            'tool_call_id': tool_call_id,
            'message': result["message"]
        }, room=session_id)
        session_store[session_id]['state'] = serialize_convo_state(conversation_state)
        return
    
    tool_message = ToolMessage(content=str(result), tool_call_id=tool_call_id)
    
    conversation_state['user_input'] = user_response
    conversation_state['messages'].append(tool_message)
    conversation_state.update(result)
    updated_state = process_message(conversation_state, session_id, config)
    session_store[session_id]['state'] = serialize_convo_state(updated_state)

def process_message(state, session_id, config):
    events = part_1_graph.stream(state, config, stream_mode="values")
    
    for event in events:
        message = event.get("messages")
        if message:
            if isinstance(message, list):
                message = message[-1]
            if message.id not in _printed:
                if isinstance(message, AIMessage):
                    if len(message.content.strip()) > 0:
                        socketio.emit('bot_response', {'message': message.content}, room=session_id)
                    if message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_name = tool_call["name"]
                            tool_call_id = tool_call["id"]
                            if tool_name == "AskContactPermissionTool":
                                if check_all_required_info(state) and state['contact_permission'] is None:
                                    question = "Do you give permission for us to contact you through email or phone number provided?* (Please type: yes/y or no/n) \n * **You understand that by typing 'yes' or 'y', you are providing your consent for a ClearOne Advantage representative or one of our marketing partners or network providers to contact you by email, text and phone, which may include pre-recorded messages and use automated technology. Your consent to such contact is not required as a condition to use a network service provider. You can unsubscribe at any time.** "
                                    latest_tool_call = {
                                        'tool_name': tool_name,
                                        'tool_call_id': tool_call_id,
                                        'message': question
                                    }
                                    state['messages'].append(message)
                                    _print_event(event, _printed)
                                    socketio.emit('user_input_required', latest_tool_call, room=session_id)
                                    return state
                                else:
                                    socketio.emit('bot_response', {'message': "Must collect the list of required customer information first."}, room=session_id)
                            if tool_name == "AskCreditPullPermissionTool":
                                if check_all_required_info(state) and state['contact_permission'] and state['credit_pull_permission'] is None:
                                    question = "Do you give permission for us to obtain your credit profile? This will NOT affect your credit score.† (Please type: yes/y or no/n) \n † **You understand that by typing 'yes' or 'y', you are providing written instructions to ClearOne Advantage, LLC (ClearOne) under the Fair Credit Reporting Act authorizing ClearOne Advantage to obtain information from your personal credit report or other information from a credit bureau solely for debt settlement. This will not impact your credit.** "
                                    latest_tool_call = {
                                        'tool_name': tool_name,
                                        'tool_call_id': tool_call_id,
                                        'message': question
                                    }
                                    state['messages'].append(message)
                                    _print_event(event, _printed)
                                    socketio.emit('user_input_required', latest_tool_call, room=session_id)
                                    return state
                                else:
                                    socketio.emit('bot_response', {'message': "Must collect the list of required customer information first."}, room=session_id)

        _print_event(event, _printed)
        
        # Update the state with any new information from the event
        for key in ['required_information', 'contact_permission', 'credit_pull_permission', 
                    'credit_pull_complete', 'lead_create_complete', 'savings_estimate', 'reason_for_decline']:
            if key in event:
                state[key] = event[key]

    state['messages'].append(message)
    return state

def generate_initial_message(config):
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
    
    return "Hello! I'm Claire, a debt resolution specialist at ClearOne Advantage. How can I assist you today? May I have your first name to get started?"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port)