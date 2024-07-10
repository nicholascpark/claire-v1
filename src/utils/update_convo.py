import json
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableLambda

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

update_convo_state = RunnableLambda(update_convo_state)