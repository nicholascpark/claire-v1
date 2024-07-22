from typing import Dict, Any
from langchain_core.tools import Tool, tool
from src.state import RequiredInformation

@tool
def savings_estimate_tool(required_information, contact_permission, credit_pull_permission, credit_pull_complete, lead_create_complete, savings_estimate, reason_for_decline) -> Dict[str, Any]:
    """After the lead create tool is complete, this tool calculates the potential savings estimate for the customer."""

    if lead_create_complete is None:
        return {"message": "Cannot calculate savings estimate without creating a lead first."}
    
    if not lead_create_complete:
        return {"message": "Not eligible to the program. Cannot calculate savings estimate."}
    
    # required_info = inputs.get("required_information", RequiredInformation())
    # all_info_filled = all(required_information.get(field) is not None for field in required_information)
    all_info_filled = all(v is not None for k, v in required_information.items())

    if not all_info_filled:
        return {"message": "Need to collect all the required information to calculate the savings estimate."}

    if credit_pull_complete is not None and savings_estimate is None:
        debt = required_information["Debt"]
        print("Program Eligible Debt:", debt)
        if credit_pull_complete and debt <= 7500:
            return {"message": "The customer is not eligible for the program."}

        savings = round(debt * 0.23)
        payment = max(250, round((debt - savings) / 48))
        settlement = round(debt * 0.5)
        program_length = round(((debt - savings) / payment) / 12, 1)

        return {
            "debt": "$" + str(debt),
            "savings": "$" + str(savings),
            "payment": "$" + str(payment),
            "settlement": "$" + str(settlement),
            "program_length": str(program_length) + " years"
        }
    else:
        return {"message": "Provide the required information and complete the credit pull and lead creation tools first."}

# class SavingsEstimateTool(Tool):
#     name: str = "SavingsEstimateTool"
#     description: str = "Once the lead create api tool is complete and debt info collected, this tool calculates the potential savings estimate for the customer.",
#     func = calculate_savings_estimate
        
# savings_estimate_tool = SavingsEstimateTool(
#         name="SavingsEstimateTool",
#         description="Once the lead create tool is complete, this tool calculates the potential savings estimate for the customer.",
#         func=calculate_savings_estimate
#         )