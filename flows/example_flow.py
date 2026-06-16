from pipecat_flows import (
    FlowArgs,
    FlowManager,
    FlowsFunctionSchema,
    NodeConfig
)

def create_initial_node() -> NodeConfig:
    """
    creates the initial node for the flow
    """

    record_favorite_color_func = FlowsFunctionSchema(
        name="record_favorite_color_func",
        required=['color'],
        description="Asks the user's favorite color and said is their favorite color",
        handler=record_favorite_color_and_set_next_node,
        properties={"color":{"type":"string"}}
    )

    return NodeConfig(
        name="initial",
        role_message="You are an inquisitive child. Use very simple language. Ask simple questions. You must ALWAYS use one of the available functions to progress the conversation. Your responses will be converted to audio. Avoid outputting special characters and emojis.",
        task_messages=[
            {
                "role":"developer",
                "content": "Say, 'hello world' and ask what is the user's favorite color.",
            },            
        ],
        functions=[record_favorite_color_func]
    )

async def record_favorite_color_and_set_next_node(
        args: FlowArgs, flow_manager: FlowManager
) -> tuple[str, NodeConfig]:
    """
    Function handler to record the user's favorite color and move to next node
    """
    print(f"user's favorite color is {args['color']}")
    return args['color'], create_end_node()



def create_end_node() -> NodeConfig:
    """End node to greet the user and end the conversation smoothly"""

    return NodeConfig(
        name="create_end_node",
        task_messages=[
            {
                "role" : "developer",
                "content" : "Thank the user for answering and end the conversation."
            }
        ],
        post_actions=[{"type":"end_conversation"}]
    )