from pipecat_flows import (
    FlowArgs,
    FlowManager,
    NodeConfig,
    FlowsFunctionSchema
)
import json

def create_initial_node(name: str) -> NodeConfig:

    decision_func = FlowsFunctionSchema(
        name="decision_func",
        handler=decision_func_handler,
        description="Retrives the decision by the user for whether they want to continue the call or not.",
        required=['decision'],
        properties={'decision': {'type': 'boolean'}}
    )

    with open('system_prompt.txt', 'r') as file:
        prompt = file.read()

    return NodeConfig(
        name="Initial Node",
        functions=[decision_func],
        role_message=prompt,
        task_messages=[
            {
                "role":"developer",
                "content":f"Greet the user with a warm greeting the name of the user is {name}, introduce yourself briefly and the ask the user whether they are available to converse with for a few minutes. "
            }
        ]
    )

async def decision_func_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[dict | NodeConfig]:
    decision = args['decision']

    if not decision:
        return {
            "status": False
        }, create_end_node()
    
    return {"status": True}, create_inquiry_node()

def create_inquiry_node() -> NodeConfig:

    inquiry_information = FlowsFunctionSchema(
        name="inquiry_information_collector",
        description="Inquire the user about their property needs.",
        handler=inquiry_information_handler,
        required=['purpose', 'location', 'budget'],
        properties={
            "purpose": {
                "type": "string",
                "description": "The user's stated purpose, e.g. 'buy' or 'rent'. Do not include the question, only the user's answer."
            },
            "location": {
                "type": "string",
                "description": "The specific location or area the user wants, e.g. 'South Delhi'."
            },
            "budget": {
                "type": "string",
                "description": "The user's stated budget amount, e.g. '1 lakh'."
            }
        }
        )

    return NodeConfig(
        name="Inquiry Node",
        task_messages=[
            {
                "role":"developer",
                "content":"Ask the user about their property requirements: purpose (buy/rent), preferred location, and budget."
            }
        ],
        functions=[inquiry_information]
    )

async def inquiry_information_handler(args: FlowArgs, flow_manager: FlowManager) -> tuple[ dict | NodeConfig]:
    information = {
        "type": args['purpose'],
        "location": args['location'],
        "budget": args['budget']
    }
    print(information)
    if not all(list(information.values())):
        return {"status": False}, create_inquiry_node()

    with open("info.json", "w") as file:
        json.dump(information, file, ensure_ascii=False)
    
    return {"status": True}, create_end_node()

def create_end_node()-> NodeConfig:
    return NodeConfig(
        name="End Node",
        task_messages=[{
            "role": "developer",
            "content": "Thank the user for connecting with you, and ask them to reach out later if they have any queries in the future and end the conversation."
        }],
        post_actions=[
            {"type": "end_conversation"}
        ]
    )