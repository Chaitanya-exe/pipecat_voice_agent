from pipecat_flows import (
    FlowArgs,
    FlowManager,
    NodeConfig,
    FlowsFunctionSchema
)
import requests
import httpx

async def get_location(city: str):
    url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={city}&count=1"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()

    if not data.get("results"):
        return None
    
    result = data['results'][0]

    return {
        "lat": result['latitude'],
        "lon": result['longitude']
    }


async def get_weather(lat: float, lon: float):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,weather_code"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()
 
def create_initial_node() -> NodeConfig:
    """
    creates the initial node to start the flow.
    """

    retrive_location_func = FlowsFunctionSchema(
        name="retrieve_weather_information_func",
        handler=retrive_location_and_get_weather,
        description="Retrieves weather information by location.",
        required=['city'],
        properties={'city': {'type': 'string'}}
    )

    return NodeConfig(
        name="initial_node",
        role_message="You are a helpful assistant who talks politely and friendly. You must ALWAYS use one of the available functions to progress the conversation. Your responses will be converted to audio. Avoid outputting special characters and emojis.",
        task_messages=[
            {
                "role":"developer",
                "content": "Greet the user with a warm greeting. Ask the name of city for which the user want to know the weather of."
            }
        ],
        functions=[retrive_location_func]
    )

async def retrive_location_and_get_weather(args: FlowArgs, flow_manager: FlowManager) -> tuple[dict, NodeConfig]:
    city = args['city']
    print(f"user asked about the weather of {city}")
    cords = await get_location(city)

    if not cords:
        return {
            "success": False,
            "message": "city not found"
        }, create_initial_node()

    weather = await get_weather(lat=cords['lat'], lon=cords['lon'])

    return {
        "success": True,
        "city": city,
        "temperature": weather['current']['temperature_2m'],
        "humidity": weather['current']['relative_humidity_2m'],
    }, create_end_node()



def create_end_node():
    """Tell the weather information to the user and end conversation"""

    return NodeConfig(
        name="end_node",
        task_messages=[
            {
                "role":"developer",
                "content": "Tell the user about the weather information in a nice and polite way, greet the user to have a nice day and then end the conversation."
            }
        ],
        post_actions=[{"type":"end_conversation"}]
    )