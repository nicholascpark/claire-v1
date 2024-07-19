import json
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda
from src.utils.info_collector import check_all_required_info
from typing import Dict

def update_convo_state(state: dict):
    messages = state.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, ToolMessage):
            # print("Check this:", message)
            try:
                tool_response = json.loads(message.content)
                # Credit Pull API response
                if "Data" in tool_response and "TotalEligibleDebt" in tool_response["Data"]:
                    if tool_response["Success"]:
                        state["required_information"].Debt = float(tool_response["Data"]["TotalEligibleDebt"])
                        print(f"Updated Debt in required_information: {state['required_information'].Debt}")
                    state["credit_pull_complete"] = tool_response["Success"]
                # Lead Create API response
                if "Data" in tool_response and "IsDuplicate" in tool_response["Data"]:
                    state["lead_create_complete"] = tool_response["Success"]
                    if tool_response["Data"]["IsDuplicate"]:
                        state["reason_for_decline"] = tool_response["Message"]
                if "contact_permission" in tool_response:
                    state["contact_permission"] = tool_response["contact_permission"]
                    print(f"Updated contact_permission: {state['contact_permission']}")
                    if not state["contact_permission"]:
                        state["reason_for_decline"] = "User did not give contact permission."
                if "credit_pull_permission" in tool_response:
                    if not tool_response["credit_pull_permission"]:
                        state["credit_pull_complete"] = False
                    state["credit_pull_permission"] = tool_response["credit_pull_permission"]
                    print(f"Updated credit_pull_permission: {state['credit_pull_permission']}")
                if "saving_estimate" in tool_response:
                    state["savings_estimate"] = tool_response
                    print(f"Updated savings_estimate: {state['savings_estimate']}")
                break
            except json.JSONDecodeError:
                continue

    print("Updated state: \n")
    print(state["required_information"].dict())
    print(state["contact_permission"])
    print(state["credit_pull_permission"])
    print(state["credit_pull_complete"])
    print(state["lead_create_complete"])
    print(state["savings_estimate"])
    return state


def handle_contact_permission(conversation_state, response: str) -> Dict[str, bool]:
    if not check_all_required_info(conversation_state):
        return {"message": "Collect the list of required information first."}
    
    if conversation_state.get("contact_permission") is not None:
        return {"message": "Contact permission already obtained."}
    
    if response in ['y', 'yes']:
        return {"contact_permission": True}
    elif response in ['n', 'no']:
        return {"contact_permission": False}
    else:
        return {"message": "Invalid input. Do you give permission for us to contact you through email or phone number provided?* (Please type: yes/y or no/n)"}

def handle_credit_pull_permission(conversation_state, response: str) -> Dict[str, bool]:

    print("check_all_required_info(conversation_state):", check_all_required_info(conversation_state))
    if not check_all_required_info(conversation_state):
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
        return {"message": "Invalid input. Do you give permission for us to perform a soft pull on your credit profile? This will NOT affect your credit score.** (Please type: yes/y or no/n)"}
