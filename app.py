from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from src.state import ConvoState, RequiredInformation
from src.graph.builder import create_graph
from src.utils.misc import _print_event
from langchain_core.messages import SystemMessage, HumanMessage
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

part_1_graph = create_graph()
thread_id = str(uuid.uuid4())
config = {
    "configurable": {
        "thread_id": thread_id,
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected')
    initial_message = generate_initial_message()
    emit('bot_response', {'message': initial_message})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def generate_initial_message():
    initial_state = ConvoState(
        user_input="",
        messages=[HumanMessage(content=".")],
    )
    events = part_1_graph.stream(initial_state, config, stream_mode="values")
    for event in events:
        if 'messages' in event:
            for msg in event['messages']:
                if not isinstance(msg, HumanMessage):
                    return msg.content

@socketio.on('user_message')
def handle_message(message):
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    initial_state = ConvoState(
        user_input=message,
        messages=[HumanMessage(content=message)],
    )
    _printed = set()
    events = part_1_graph.stream(initial_state, config, stream_mode="values")
    for event in events:
        _print_event(event, _printed)
        if 'messages' in event:
            for msg in event['messages']:
                if not isinstance(msg, HumanMessage):
                    emit('bot_response', {'message': msg.content})

@socketio.on('quit')
def handle_quit():
    emit('bot_response', {'message': "You have successfully quit the chat. Refresh the page to start a new conversation."})

if __name__ == '__main__':
    socketio.run(app, debug=True)