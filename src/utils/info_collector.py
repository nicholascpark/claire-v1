from langchain_core.messages import ToolMessage, SystemMessage
import pgeocode
import pandas as pd
from typing import List
from src.state import RequiredInformation, ConvoState
from src.prompts import info_collector_prompt
# from langchain_openai import ChatOpenAI
from src.config import llm

# llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature = 0, max_tokens = 1000)

def get_city_state(zip_code):
    nomi = pgeocode.Nominatim('us')  # Use 'us' for United States, change as needed
    location = nomi.query_postal_code(zip_code)
    
    if pd.notnull(location.place_name) and pd.notnull(location.state_code):
        return location.place_name, location.state_code
    else:
        return None, None

def collect_info(state: ConvoState):
    collect_info_chain = info_collector_prompt | llm.with_structured_output(RequiredInformation)
    result = collect_info_chain.invoke({
            "messages": state["messages"],
            "provided_so_far": state["required_information"],
            "user_input": state["user_input"],
    })
    
    # If Zip is provided but City or State is missing, try to infer them
    if result.Zip and (not result.City or not result.State):
        try: 
            city, state_abbr = get_city_state(result.Zip)
            if city and state_abbr:
                result.City = city
                result.State = state_abbr
                state["messages"].append(SystemMessage(content=f"Inferred City: {city}, Inferred State: {state_abbr}"))
            else: 
                state["messages"].append(SystemMessage(content=f"Cannot infer city and state from this zip code ({result.Zip}), please check again."))
        except ValueError as e:
            state["messages"].append(SystemMessage(content=f"{e} \nInvalid zip code ({result.Zip}), please check again."))

    # If Zip is provided again differently, update the City and State
    if state.get("required_information") and (result.Zip != state["required_information"].Zip) and (result.City or result.State):
        try: 
            city, state_abbr = get_city_state(result.Zip)
            if city and state_abbr:
                if city != result.City or state_abbr != result.State:
                    result.City = city
                    result.State = state_abbr
                    state["messages"].append(SystemMessage(content=f"Updated City: {city}, Updated State: {state_abbr}"))
            else: 
                state["messages"].append(SystemMessage(content=f"Cannot infer city and state from this zip code ({result.Zip}), please check again."))
        except ValueError as e:
            state["messages"].append(SystemMessage(content=f"{e} \nInvalid zip code ({result.Zip}), please check again."))

    if "required_information" in state:
        required_info = combine_required_info(
            info_list=[state.get("required_information"), result]
        )
    else:
        required_info = result
    return {
        "required_information": required_info,
        "messages": state["messages"]
    }

def combine_required_info(info_list: List[RequiredInformation]) -> RequiredInformation:
    info_list = [info for info in info_list if info is not None]

    if len(info_list) == 1:
        return info_list[0]
    combined_info = {}
    for info in info_list:
        for key, value in info.dict().items():
            if value is not None:
                combined_info[key] = value
    return RequiredInformation(**combined_info)