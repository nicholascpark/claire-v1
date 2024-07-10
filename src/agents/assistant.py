from langchain_core.runnables import Runnable, RunnableConfig
from src.state import ConvoState, RequiredInformation
from src.utils.info_collector import collect_info, combine_required_info
from typing import Any, Dict

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: ConvoState, config: RunnableConfig):
        while True:
            result = self.runnable.invoke(state)
            # print(result.tool_calls)
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        # Collect and update required information
        collected_info = collect_info(state)
        updated_required_info = combine_required_info([state.get("required_information", RequiredInformation()), collected_info["required_information"]])
        state = {**state, "required_information": updated_required_info}
        # print(updated_required_info.dict())
        if result.tool_calls:
            result = self.process_tool_calls(result, state)
        
        return {
            "messages": result,
            "required_information": updated_required_info
        }
    
    def process_tool_calls(self, result, state):
        # required_info = state.get("required_information", RequiredInformation())
        # all_info_filled = all(getattr(required_info, field) is not None for field in required_info.__fields__)
        
        print("Result before:", result)

        new_tool_calls = []
        for tool_call in result.tool_calls:
            # tool_name = tool_call["name"]

            modify_with = {k: v for k, v in state.items() if k not in ["messages", "user_input"]}
            modify_with["required_information"] = {**state["required_information"].dict(), "LeadId": 999}
            new_tool_calls.append(self.modify_tool_args(tool_call, modify_with = modify_with))
        
        result.tool_calls = new_tool_calls
        
        print("Result after:", result)

        return result

    def modify_tool_args(self, tool_call: Dict[str, Any], modify_with: Dict[str, Any]) -> Dict[str, Any]:
        if "args" in tool_call:
            if isinstance(tool_call["args"], dict) and "__arg1" in tool_call["args"]:
                tool_call["args"]["__arg1"] = modify_with
            else:
                tool_call["args"] = modify_with
        else:
            tool_call["args"] = modify_with
        return tool_call