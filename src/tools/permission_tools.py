
from typing import Dict, Any
from langchain.tools import Tool
from src.state import RequiredInformation

def ask_contact_permission(inputs) -> Dict[str, bool]:

    pass

def ask_credit_pull_permission(inputs) -> Dict[str, bool]:
    
    pass


class AskContactPermissionTool(Tool):
    name: str = "AskContactPermissionTool"
    description: str = "Ask the user for permission to contact them and process their response."
    func = ask_contact_permission

    def invoke(*args, **kwargs):
        return {"message": "Move to the next tool."}

class AskCreditPullPermissionTool(Tool):
    name: str = "AskCreditPullPermissionTool"
    description: str = "Ask the user for permission to pull their credit and process their response."
    func = ask_credit_pull_permission

    def invoke(*args, **kwargs):
        return {"message": "Move to the next tool."}

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