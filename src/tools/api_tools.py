from langchain_core.tools import Tool
from typing import Dict, Any, List, Union
import requests
import os

def run_credit_pull_api(inputs) -> Dict[str, Any]:

    if not inputs.get("credit_pull_permission"):
        return {"message": "Please obtain credit pull permission first."}

    request_data = inputs["required_information"]
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

    print("Credit Pull Status Code:", response.status_code)
        
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
        headers={"APIKEY": F"{os.getenv("CLEARONE_LEADS_API_KEY")}"}
    )

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f'HTTP error occurred: {err}')
    except Exception as err:
        print(f'Other error occurred: {err}')   

    result = response.json()

    print("Lead Create Status Code:", response.status_code)

    return result


class CreditPullAPITool(Tool):
    name: str = "CreditPullAPI"
    description: str = "Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to pull the customer's credit report."
    
    def _run(self, tool_input: Union[List, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        if isinstance(tool_input, list) and "Debt" in tool_input[0]:
            # Handle string input if necessary
            tool_input = {"required_information": tool_input[0]}
        try:
            required_info = tool_input.get("required_information", tool_input)
            results = run_credit_pull_api(required_info)
            print("Credit Pull Response:", results)
            return results
        except requests.RequestException as e:
            raise ValueError(f"Request failed: {str(e)}")
        except Exception as e:
            raise ValueError(f"An error occurred: {str(e)}")

    # async def _arun(self, tool_input: Union[List, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    #     # Implement the async version if needed
    #     return await run_in_executor(None, self._run, tool_input, **kwargs)

class LeadCreateAPITool(Tool):
    name: str = "LeadCreateAPI"
    description: str = "Once all the required customer info is collected, this makes a POST request to the ClearOne Advantage API to create a new lead in Salesforce."
    
    def _run(self, tool_input: Union[List, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        if isinstance(tool_input, list) and "Debt" in tool_input[0]:
            # Handle string input if necessary
            tool_input = {"required_information": tool_input[0]}
        
        try:
            required_info = tool_input.get("required_information", tool_input)
            results = run_lead_create_api(required_info)
            print("Lead Create Response:", results)
            return results
        except requests.RequestException as e:
            raise ValueError(f"Request failed: {str(e)}")
        except Exception as e:
            raise ValueError(f"An error occurred: {str(e)}")

    # async def _arun(self, tool_input: Union[str, Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
    #     # Implement the async version if needed
    #     return await run_in_executor(None, self._run, tool_input, **kwargs)
        
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