from langchain_core.tools import BaseTool,tool
from typing import Dict, Any, List, Union
import requests
import os


@tool
def credit_pull_api_tool(required_information, contact_permission, credit_pull_permission, credit_pull_complete, lead_create_complete, savings_estimate, reason_for_decline) -> Dict[str, Any]:
    """Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to pull the customer's credit report."""

    if not credit_pull_permission:
        return {"message": "Please obtain credit pull permission first."}

    request_data = required_information
    # Make the POST request
    response = requests.post(
        "https://carbon.clearoneadvantage.com/api/affiliate/creditpull",
        json=request_data,
        headers={"APIKEY": F"{os.getenv("CLEARONE_LEADS_API_KEY")}"}
    )
    
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'HTTP error occurred: {err}')  
    except Exception as err:
        print(f'Other error occurred: {err}')   
        
    return response.json()

@tool
def lead_create_api_tool(required_information, contact_permission, credit_pull_permission, credit_pull_complete, lead_create_complete, savings_estimate, reason_for_decline) -> Dict[str, Any]:
    """Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to create a new lead in Salesforce."""

    if not contact_permission:
        return {"message": "Obtain contact permission first."}
    
    # if credit_pull_complete is None:
    if not credit_pull_complete:
        return {"message": "Ask for credit pull permission first."}

    request_data = required_information
    # Make the POST request
    response = requests.post(
        "https://carbon.clearoneadvantage.com/api/lead/create?detailedResponse=true",
        json=request_data,
        headers={"APIKEY": F"{os.getenv("CLEARONE_LEADS_API_KEY")}"}
    )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'HTTP error occurred: {err}')
    except Exception as err:
        print(f'Other error occurred: {err}')   

    result = response.json()

    return result

# class CreditPullAPITool(BaseTool):
#     name: str = "CreditPullAPI"
#     description: str = "Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to pull the customer's credit report."
#     func = run_credit_pull_api
    
#     def _run(self, required_information, contact_permission, credit_pull_permission, credit_pull_complete, lead_create_complete, savings_estimate, reason_for_decline) -> Dict[str, Any]:
#         try:
#             return run_credit_pull_api(required_information)
        
#         except requests.RequestException as e:
#             # Handle request-related errors
#             raise ValueError(f"Request failed: {str(e)}")
        
#         except Exception as e:
#             # Handle other errors
#             raise ValueError(f"An error occurred: {str(e)}")
                
# class LeadCreateAPITool(BaseTool):
#     name: str = "LeadCreateAPI"
#     description: str = "Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to create a new lead in Salesforce."
#     func = run_lead_create_api

#     def _run(self, **kwargs) -> Dict[str, Any]:
#         try:
#             return run_credit_pull_api(kwargs.get("required_information"))
        
#         except requests.RequestException as e:
#             # Handle request-related errors
#             raise ValueError(f"Request failed: {str(e)}")
        
#         except Exception as e:
#             # Handle other errors
#             raise ValueError(f"An error occurred: {str(e)}")
        
# class CreditPullAPITool(BaseTool):
#     name: str = "CreditPullAPI"
#     description: str = "Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to pull the customer's credit report."
#     func = run_credit_pull_api
    
#     def _run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
#         try:
#             # Call the function with the input data
#             required_info = input_data["required_information"]
#             results = self.func(required_info)
#             print("Credit Pull Response:", results)
#             return results
        
#         except requests.RequestException as e:
#             # Handle request-related errors
#             raise ValueError(f"Request failed: {str(e)}")
        
#         except Exception as e:
#             # Handle other errors
#             raise ValueError(f"An error occurred: {str(e)}")
        
# class LeadCreateAPITool(BaseTool):
#     name: str = "LeadCreateAPI"
#     description: str = "Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to create a new lead in Salesforce."
#     func = run_lead_create_api

#     def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
#         try:
#             # Call the function with the input data
#             required_info = input_data["required_information"]
#             results = self.func(required_info)
#             print("Lead Create Response:", results)
#             return results
        
#         except requests.RequestException as e:
#             # Handle request-related errors
#             raise ValueError(f"Request failed: {str(e)}")
        
#         except Exception as e:
#             # Handle other errors
#             raise ValueError(f"An error occurred: {str(e)}")
        

# Usage example
# credit_pull_api_tool = CreditPullAPITool(
#         name="CreditPullAPI",
#         description="Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to pull the customer's credit report.",
#         func=run_credit_pull_api
#         )

# lead_create_api_tool = LeadCreateAPITool(
#         name="LeadCreateAPI",
#         description="Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to create a new lead in Salesforce.",
#         func=run_lead_create_api
#         )
