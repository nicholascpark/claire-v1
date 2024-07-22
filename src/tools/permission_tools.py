
from typing import Dict, Any
from langchain.tools import Tool
from src.state import RequiredInformation

def ask_contact_permission(inputs) -> Dict[str, bool]:

    required_info = inputs.get("required_information")
    all_info_filled = all(required_info.get(field) is not None for field in required_info)

    if not all_info_filled:
        return {"message": "Collect the list of required information first."}
    
    if inputs.get("contact_permission") is not None:
        return {"message": "Already done. Move on to the next tool."}
    
    while all_info_filled and inputs.get("contact_permission") is None:
        response = input("TCPA Consent: Do you give permission for us to contact you through email or phone number provided? (Please type: yes/y or no/n): ").lower()
        if response in ['y', 'yes']:
            return {"contact_permission": True}
        elif response in ['n', 'no']:
            return {"contact_permission": False, "message": "User has not given permission to be contacted. We cannot proceed without the contact permission."}
        else:
            print("Invalid input. Please answer with 'yes/y' or 'no/n'.")

def ask_credit_pull_permission(inputs) -> Dict[str, bool]:
    
    required_info = inputs.get("required_information")
    all_info_filled = all(required_info.get(field) is not None for field in required_info)

    if not all_info_filled:
        return {"message": "Collect the list of required information first."}
    
    if not inputs.get("contact_permission"):
        return {"message": "Obtain the contact permission first."}
    
    if inputs.get("credit_pull_permission") is not None:
        return {"message": "Already done. Move on to the next tool."}

    while all_info_filled and inputs.get("credit_pull_permission") is None and inputs.get("contact_permission"):         
        response = input("Credit Pull Consent: Do you give permission for us to pull your credit? This will NOT affect your credit score. (Please type: yes/y or no/n): ").lower()
        if response in ['y', 'yes']:
            return {"credit_pull_permission": True}
        elif response in ['n', 'no']:
            return {"credit_pull_permission": False}
        else:
            print("Invalid input. Please answer with 'yes/y' or 'no/n'.")


class AskContactPermissionTool(Tool):
    name: str = "AskContactPermissionTool"
    description: str = "Ask the user for permission to contact them and process their response."
    func = ask_contact_permission

    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, bool]:
        return self.func()

class AskCreditPullPermissionTool(Tool):
    name: str = "AskCreditPullPermissionTool"
    description: str = "Ask the user for permission to pull their credit and process their response."
    func = ask_credit_pull_permission

    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, bool]:
        return self.func()

# Create instances of the tools
ask_contact_permission_tool = AskContactPermissionTool(
    name="AskContactPermissionTool",
    description="Ask the user for permission to contact them and process their response. This is the first tool to call after collecting the required information.",
    func=ask_contact_permission
)

ask_credit_pull_permission_tool = AskCreditPullPermissionTool(
    name="AskCreditPullPermissionTool",
    description="Ask the user for permission to pull their credit and process their response. This is a required step before using the credit pull API tool.",
    func=ask_credit_pull_permission
)