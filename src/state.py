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

class ConvoState(TypedDict):
    user_input: str
    messages: Annotated[list[AnyMessage], add_messages]
    required_information: RequiredInformation
    contact_permission: bool
    credit_pull_permission: bool
    credit_pull_complete: bool
    lead_create_complete: bool
    savings_estimate: dict
    reason_for_decline: Optional[str]