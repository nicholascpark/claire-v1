from langchain_core.tools import BaseTool,tool
from typing import Dict, Any, List, Union
import requests
import os

# @tool
# def form_submission_tool(required_information, contact_permission, credit_pull_permission, credit_pull_complete, lead_create_complete, savings_estimate, reason_for_decline) -> Dict[str, Any]:
#     # """This tool is called when the user submits the form. It collects the user's information and updates the state."""
#     # # Collect the user's information
#     # collected_info = required_information
#     # # Update the state with the collected information
#     # updated_required_info = {**required_information, **collected_info}
    
#     # return updated_required_info
#     pass

import uuid

def webform_payload(required_info):
    print("Required Info:", required_info)
    # required_info = state['required_information']
    return {"payload": {
                "pathname": "/ps/cc-debt-relief",
                "funnel": {
                    "id": "coa_ps_long",
                    "label_next": "Continue",
                    "label_previous": "",
                    "name": "PS - Long",
                    "title": "Credit Card Debt Relief Savings Estimate!",
                    "subtitle": "Get a personalized plan including an estimate of your total savings.",
                    "tracks": {
                        "A": [
                            {
                                "name": "Debt Types",
                                "title": "What types of debt do you have?"
                            },
                            {
                                "name": "Bills",
                                "title": "Do you need immediate relief because you can't afford current bills or next month's payments?"
                            },
                            {
                                "name": "Estimated Debt",
                                "title": "How much debt do you have?",
                                "label_next": "Continue"
                            },
                            {
                                "name": "No Questions",
                                "title": "You have multiple options!",
                                "text": "Based on your situation, there are multiple debt relief options available to help you get out of debt."
                            },
                            {
                                "name": "Name / Zip / Phone",
                                "title": "Tell us more about yourself!",
                                "text": "Get your estimated monthly savings, total savings, and see how quickly debts can be resolved."
                            },
                            {
                                "name": "Loan",
                                "title": "Need a loan?",
                                "text": "Debt consolidation is NOT the same as a loan."
                            },
                            {
                                "name": "Street / DOB (Alt 1)",
                                "title": "Relief request for you.",
                                "text": "Next, we will gather your statements and bills, get a snapshot of your debts, and connect you to your personalized savings estimate.",
                                "label_next": "View Estimate"
                            }
                        ]
                    }
                },
                "interaction": {
                    "phone": "888-340-4697",
                    "journey": [
                        "Landing",
                        "Step 1 (ANON)",
                        "Step 2 (ANON)",
                        "Step 3 (ANON)",
                        "Step 4 (ANON)",
                        "Step 5 (FQL)",
                        "Step 6 (FQL)",
                        "Step 7 (FQC)"
                    ],
                    "segment": "FQC",
                    "step": 7,
                    "track": "A",
                    "id": "9ea9cdc9-71ff-45e0-9247-c67ed7dd3138"
                },
                "profile": {
                    "id": "db7ea855-0ac7-4c34-ae95-3668c5ab96ee",
                    "date_of_birth": required_info.get("DateOfBirth"),
                    "email": required_info.get("Email"),
                    "first_name": required_info.get("FirstName"),
                    "last_name": required_info.get("LastName"),
                    "mobile_phone": "5555555555"
                },
                "visitor": {
                    "ip_address": "69.136.173.35",
                    "landing_uri": "https://quote.clearoneadvantage.com/ps/cc-debt-relief/",
                    "query_params": {
                        "utm_test": "test1",
                        "utm_arb": "arb1"
                    },
                    "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                    "xxTrustedFormToken": "https://cert.trustedform.com/7fbf4e31ae51a60a80a768b9f59dcf1707c73ab6",
                    "xxTrustedFormCertUrl": "https://cert.trustedform.com/7fbf4e31ae51a60a80a768b9f59dcf1707c73ab6",
                    "xxTrustedFormPingUrl": "https://ping.trustedform.com/0.V_g3YopbbVYB2G3JTaZTvIKwZWNGFgnKJN5H61XUeWvcBpCHkD9U4sQk1HanbtqdB4sxfSM.oYJg6NDk8ARnErfpwsyoPA.aIxLUe7_qFGzLDg_kuZZWg",
                    "hutk": "3fdf3f84e0d544e14d713f635b5dceb7"
                },
                "form": {
                    "q_debt_types": [
                        "Retail Card Debt"
                    ],
                    "q_bills": "No",
                    "q_debt_amount": required_info.get("Debt"),
                    "first_name": required_info.get("FirstName"),
                    "last_name": required_info.get("LastName"),
                    "email": required_info.get("Email"),
                    "postal_code": required_info.get("Zip"),
                    "mobile_phone": convert_phone_number(required_info.get("Phone")),
                    "city": required_info.get("City"),
                    "us_state": required_info.get("State"),
                    "consent_tcpa": "true",
                    "q_loan": "No",
                    "street_address": required_info.get("Address"),
                    "date_of_birth": required_info.get("DateOfBirth"),
                    "consent_credit_pull": "true"
                }
            }
        }

def convert_phone_number(phone_number):
    if len(phone_number) == 10 and phone_number.isdigit():
        return f"{phone_number[:3]}-{phone_number[3:6]}-{phone_number[6:]}"
    else:
        raise ValueError("Invalid phone number format. Please provide a 10-digit phone number without spaces or dashes.")
    
@tool
def submission_webform_api_tool(required_information, contact_permission, credit_pull_permission, credit_pull_complete, lead_create_complete, savings_estimate, reason_for_decline) -> Dict[str, Any]:
    """Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API endpoint to submit the web form."""

    if not contact_permission:
        return {"message": "Obtain contact permission first."}
    
    if not credit_pull_complete and credit_pull_permission:
        return {"message": "Call the CreditPullAPITool first."}
    
    # if not credit_pull_permission:
    #     pass
    transformed_data = webform_payload(required_information)
    print("Transformed Data: \n\n", transformed_data)

    response = requests.post(
            "https://quote.clearoneadvantage.com/api/funnel/form/",
            json=transformed_data,
            headers={"APIKEY": F"{os.getenv("CLEARONE_LEADS_API_KEY")}"}
        )
    try:
        response.raise_for_status()
        response_data = response.json()
        print("Webform Submission Response:", response_data)
        return response_data
    except requests.exceptions.HTTPError as err:
        print(f'HTTP error occurred: {err}')
        return {"success": False, "message": str(err)}
    except Exception as err:
        print(f'Other error occurred: {err}')
        return {"success": False, "message": str(err)}


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
    print("Credit Pull Response:", response.json())

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
    
    if not credit_pull_complete and credit_pull_permission:
        return {"message": "Call the CreditPullAPITool first."}
    
    ########################################################

    transformed_data = webform_payload(required_information)
    print("Transformed Data: \n\n", transformed_data)

    webform_submission_response = requests.post(
            "https://quote.clearoneadvantage.com/api/funnel/form/",
            json=transformed_data,
            headers={"APIKEY": F"{os.getenv("CLEARONE_LEADS_API_KEY")}"}
        )
    try:
        webform_submission_response.raise_for_status()
    except webform_submission_response.exceptions.HTTPError as err:
        print(f'HTTP error occurred: {err}')
    except Exception as err:
        print(f'Other error occurred: {err}')   

    result = webform_submission_response.json()

    print("Webform Submission Response:", result)

    ########################################################

    request_data = required_information
    # Make the POST request
    response = requests.post(
        "https://carbon.clearoneadvantage.com/api/lead/create?detailedResponse=true",
        json=request_data,
        # headers={"APIKEY": F"{os.getenv("CLEARONE_LEADS_API_KEY")}"}
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
