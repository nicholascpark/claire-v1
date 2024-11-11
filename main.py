from src.state import ConvoState, RequiredInformation
from src.graph.builder import create_graph
from src.utils.misc import _print_event
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
from src.utils.mssql_saver import MSSQLSaver
from typing import Dict, Any, List

def main():
    part_1_graph = create_graph()

    thread_id = str(uuid.uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    initial_human_message = HumanMessage(content=".")

    initial_state = ConvoState(
        user_input="",
        messages=[
            initial_human_message
        ],
    )

    def user_input_generator():
        yield ""
        while True:
            user_input = input("User: ")
            if user_input.lower() in ["bye claire", "bye", "quit"]:
                print("You have successfully quit the chat. Refresh the page to start a new conversation.")
                break
            yield user_input

    _printed = set()

    for user_input in user_input_generator():
        initial_state["user_input"] = user_input
        initial_state["messages"].append(HumanMessage(content=user_input))
        
        events = part_1_graph.stream(initial_state, config, stream_mode="values")
    
        for event in events:
            # print("event:", event)
            _print_event(event, _printed)

if __name__ == "__main__":
    main()
    # your_connection_string = (
    #     "DRIVER={ODBC Driver 17 for SQL Server};"
    #     "SERVER=STGDBCOA;"
    #     "DATABASE=ChatBot;"
    #     "UID=svcChatBot;"
    #     "PWD=@HMdc2wGpWEx;"
    # )
    # mssql_saver = MSSQLSaver(your_connection_string)
    # mssql_saver.reset_table()
    # thread_id = "313dc4c9-30f2-4d6c-93ec-acbff5665712" 
    # conversation_history = mssql_saver.get_conversation_history(thread_id)
    # print(conversation_history)
    # parsed_history = mssql_saver.parse_and_print_conversation_history(conversation_history)
    # print(parsed_history)
