from langchain_core.tools import Tool, StructuredTool
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
import requests
import os
from src.state import ConvoState, RequiredInformation

def run_credit_pull_api(inputs) -> Dict[str, Any]:

    if not inputs.get("credit_pull_permission"):
        return {"message": "Please obtain credit pull permission first."}

    request_data = inputs["required_information"] # if "required_information" in inputs else inputs #######
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

class CreditPullAPITool(StructuredTool):
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
        
class LeadCreateAPITool(StructuredTool):
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
        
class ConvoStateModel(BaseModel):
    user_input: str
    messages: List
    required_information: RequiredInformation
    contact_permission: Optional[bool]
    credit_pull_permission: Optional[bool]
    credit_pull_complete: Optional[bool]
    lead_create_complete: Optional[bool]
    savings_estimate: Optional[dict]
    reason_for_decline: Optional[str]

# Usage example
credit_pull_api_tool = CreditPullAPITool(
        name="CreditPullAPI",
        description="Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to pull the customer's credit report.",
        func=run_credit_pull_api,
        args_schema=ConvoStateModel
        )

lead_create_api_tool = LeadCreateAPITool(
        name="LeadCreateAPI",
        description="Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to create a new lead in Salesforce.",
        func=run_lead_create_api,
        args_schema=ConvoStateModel
        )

