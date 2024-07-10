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