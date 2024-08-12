from langchain_core.pydantic_v1 import BaseModel, Field
from typing import TypedDict, Optional, Annotated, Any
from langgraph.graph.message import AnyMessage, add_messages

class RequiredInformation(BaseModel):

    Debt: Optional[float] = Field(description="the provided debt of the user")
    FirstName: Optional[str] = Field(description="the provided first name of the user")
    LastName: Optional[str] = Field(description="the provided last name of the user")
    Zip: Optional[str] = Field(description="the provided zip code of the user")
    Phone: Optional[str] = Field(description="the provided phone number of the user")
    Email: Optional[str] = Field(description="the provided email address of the user")
    City: Optional[str] = Field(description="the provided city of the user")
    State: Optional[str] = Field(description="the provided state of the user")
    Address: Optional[str] = Field(description="the provided address of the user")
    DateOfBirth: Optional[str] = Field(description="the provided date of birth of the user")

    def all_fields_not_none(self) -> bool:
        return all(value is not None for value in self.dict().values())

class ConvoState(TypedDict):
    user_input: str
    messages: Annotated[list[AnyMessage], add_messages]
    required_information: RequiredInformation
    contact_permission: Optional[bool]
    credit_pull_permission: Optional[bool]
    credit_pull_complete: Optional[bool]
    lead_create_complete: Optional[bool]
    savings_estimate: Optional[dict]
    reason_for_decline: Optional[str]
    # session_id: Optional[str]
    # tool_calls: Optional[list[dict]]
