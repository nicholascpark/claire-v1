from langchain_core.tools import tool
from typing import Dict, Any, Callable
from langchain_core.messages import AIMessage, ToolMessage
from src.utils.handle_convo import handle_contact_permission, handle_credit_pull_permission
from src.utils.info_collector import check_all_required_info, is_dict_populated

def create_websocket_permission_tools(socket_emit: Callable):
    @tool
    def ask_contact_permission_tool(required_information, contact_permission, credit_pull_permission, credit_pull_complete, lead_create_complete, savings_estimate, reason_for_decline, session_id, tool_call) -> Dict[str, Any]:
        """Ask for contact permission from the user."""
        if is_dict_populated(required_information) and contact_permission is None:
            question = (
                "Do you give permission for us to contact you through email or phone number provided?* "
                "(Please type: yes or no) \n * **You understand that by typing 'yes', you are providing your consent "
                "for a ClearOne Advantage representative or one of our marketing partners or network providers to "
                "contact you by email, text and phone, which may include pre-recorded messages and use automated "
                "technology. Your consent to such contact is not required as a condition to use a network service "
                "provider. You can unsubscribe at any time.** "
            )
            print("tool_call_print:", tool_call)

            latest_tool_call = {
                'tool_name': tool_call['name'],
                'tool_call_id': tool_call['id'],
                'message': question
            }
            socket_emit('user_input_required', latest_tool_call, room=session_id)
        else:
            return {"message": "Must collect the list of required customer information first."}


    @tool
    def ask_credit_pull_permission_tool(required_information, contact_permission, credit_pull_permission, credit_pull_complete, lead_create_complete, savings_estimate, reason_for_decline) -> Dict[str, Any]:
        """Ask for credit pull permission from the user."""
        if is_dict_populated(required_information) and contact_permission and credit_pull_permission is None:
            question = (
                "Do you give permission for us to obtain your credit profile? This will NOT affect your credit score.† "
                "(Please type: yes or no) \n † **You understand that by typing 'yes', you are providing written "
                "instructions to ClearOne Advantage, LLC (ClearOne) under the Fair Credit Reporting Act authorizing "
                "ClearOne Advantage to obtain information from your personal credit report or other information from "
                "a credit bureau solely for debt settlement. This will not impact your credit.** "
            )
            return {
                "message": question,
                "tool_name": "AskCreditPullPermissionTool"
            }
        else:
            return {"message": "Must collect the list of required customer information and contact permission first."}

    return [ask_contact_permission_tool, ask_credit_pull_permission_tool]

def handle_contact_permission_response(conversation_state, response: str) -> Dict[str, bool]:
    if not check_all_required_info(conversation_state):
        return {"message": "Collect the list of required information first."}
    
    if conversation_state.get("contact_permission") is not None:
        return {"message": "Contact permission already obtained."}
    
    if response.strip().lower() in ['yes']:
        return {"contact_permission": True}
    elif response.strip().lower() in ['no']:
        return {"contact_permission": False}
    else:
        return {"message": "Invalid input. * Do you give permission for us to contact you through email or phone number provided? (Please type: yes or no)"}

def handle_credit_pull_permission_response(conversation_state, response: str) -> Dict[str, bool]:

    print("check_all_required_info(conversation_state):", check_all_required_info(conversation_state))
    if not check_all_required_info(conversation_state):
        return {"message": "Collect the list of required information first."}
    
    if not conversation_state.get("contact_permission"):
        return {"message": "Obtain the contact permission first."}
    
    if conversation_state.get("credit_pull_permission") is not None:
        return {"message": "Credit pull permission already obtained. Move on to the next tool."}

    if response.strip().lower() in ['yes']:
        return {"credit_pull_permission": True}
    elif response.strip().lower() in ['no']:
        return {"credit_pull_permission": False}
    else:
        return {"message": "Invalid input. † Do you give permission for us to obtain your credit profile? This will NOT affect your credit score. (Please type: yes or no)"}
