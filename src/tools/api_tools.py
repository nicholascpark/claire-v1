from langchain_core.tools import Tool
from typing import Dict, Any
import requests
import os

def run_credit_pull_api(inputs, *args) -> Dict[str, Any]:

    if not inputs.get("credit_pull_permission"):
        return {"message": "Please obtain credit pull permission first."}

    request_data = inputs["required_information"] if "required_information" in inputs else inputs #######
    # Make the POST request
    response = requests.post(
        "https://carbon.clearoneadvantage.com/api/affiliate/creditpull",
        json=request_data,
        headers={"APIKEY": F"{os.getenv("CLEARONE_LEADS_API_KEY")}"},
        # verify=False
    )
    
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'HTTP error occurred: {err}')  
    except Exception as err:
        print(f'Other error occurred: {err}')   

    print("Status Code:", response.status_code)
        
    return response.json()

def run_lead_create_api(inputs) -> Dict[str, Any]:

    if not inputs.get("contact_permission"):
        return {"message": "Obtain contact permission first."}
    
    if inputs.get("credit_pull_complete") is None:
        return {"message": "Ask for credit pull permission first."}

    request_data = inputs["required_information"]
    # Make the POST request
    response = requests.post(
        "https://carbon.clearoneadvantage.com/api/lead/create?detailedResponse=true",
        json=request_data,
        headers={"APIKEY": F"{os.getenv("CLEARONE_LEADS_API_KEY")}"},
        # verify=False
    )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'HTTP error occurred: {err}')
    except Exception as err:
        print(f'Other error occurred: {err}')   

    print("Status Code:", response.status_code)

    result = response.json()

    return result

class CreditPullAPITool(Tool):
    name: str = "CreditPullAPI"
    description: str = "Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to pull the customer's credit report."
    func = run_credit_pull_api
    
    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Call the function with the input data
            required_info = input_data["required_information"]
            results = self.func(required_info)
            print("Credit Pull Response:", results)
            return results
        
        except requests.RequestException as e:
            # Handle request-related errors
            raise ValueError(f"Request failed: {str(e)}")
        
        except Exception as e:
            # Handle other errors
            raise ValueError(f"An error occurred: {str(e)}")
        
class LeadCreateAPITool(Tool):
    name: str = "LeadCreateAPI"
    description: str = "Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to create a new lead in Salesforce."
    func = run_lead_create_api

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Call the function with the input data
            required_info = input_data["required_information"]
            results = self.func(required_info)
            print("Lead Create Response:", results)
            return results
        
        except requests.RequestException as e:
            # Handle request-related errors
            raise ValueError(f"Request failed: {str(e)}")
        
        except Exception as e:
            # Handle other errors
            raise ValueError(f"An error occurred: {str(e)}")
        

# Usage example
credit_pull_api_tool = CreditPullAPITool(
        name="CreditPullAPI",
        description="Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to pull the customer's credit report.",
        func=run_credit_pull_api
        )

lead_create_api_tool = LeadCreateAPITool(
        name="LeadCreateAPI",
        description="Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to create a new lead in Salesforce.",
        func=run_lead_create_api
        )


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
        response = input("TV: Do you give permission for us to contact you through email or phone number provided? (Please type: yes/y/no/n): ").lower()
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
        response = input("TV: Do you give permission for us to pull your credit? This will NOT affect your credit score. (Please type: yes/y/no/n): ").lower()
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

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, bool]:
        return self.func()

class AskCreditPullPermissionTool(Tool):
    name: str = "AskCreditPullPermissionTool"
    description: str = "Ask the user for permission to pull their credit and process their response."
    func = ask_credit_pull_permission

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, bool]:
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

from typing import Dict, Any
from langchain_core.tools import Tool
from src.state import RequiredInformation

def calculate_savings_estimate(inputs: Dict[str, Any]) -> Dict[str, Any]:

    if inputs.get("lead_create_complete") is None:
        return {"message": "Cannot calculate savings estimate without creating a lead first."}
    
    if not inputs.get("lead_create_complete"):
        return {"message": "Not eligible to the program. Cannot calculate savings estimate."}
    
    required_info = inputs.get("required_information", RequiredInformation())
    all_info_filled = all(required_info.get(field) is not None for field in required_info)

    if not all_info_filled:
        return {"message": "Need to collect all the required information to calculate the savings estimate."}

    if inputs.get("credit_pull_complete") is not None and inputs.get("savings_estimate") is None:
        debt = inputs["required_information"]["Debt"]
        print("Program Eligible Debt:", debt)
        if inputs.get("credit_pull_complete") and debt <= 7500:
            return {"message": "The customer is not eligible for the program."}

        savings = round(debt * 0.23)
        payment = max(250, round((debt - savings) / 48))
        settlement = round(debt * 0.5)
        program_length = round(((debt - savings) / payment) / 12, 1)

        return {
            "debt": debt,
            "savings": savings,
            "payment": payment,
            "settlement": settlement,
            "program_length": program_length
        }
    else:
        return {"message": "Provide the required information and complete the credit pull and lead creation tools first."}

class SavingsEstimateTool(Tool):
    name: str = "SavingsEstimateTool"
    description: str = "Once the debt information is collected, this tool calculates the potential savings estimate for the customer."
    func = calculate_savings_estimate

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            req_info = input_data["required_information"]
            results = self.func(req_info)
            # print("Check results:", results)
            return results
        
        except Exception as e:
            # Handle other errors
            raise ValueError(f"An error occurred: {str(e)}")
        
savings_estimate_tool = SavingsEstimateTool(
        name="SavingsEstimateTool",
        description="Once the debt information is collected, this tool calculates the potential savings estimate for the customer.",
        func=calculate_savings_estimate
        )