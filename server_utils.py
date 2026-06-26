import os

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from loguru import logger
from pydantic import BaseModel
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
load_dotenv()

class DialoutRequest(BaseModel):
    to_number: str
    from_number: str
    name: str

class TwilioCallResult(BaseModel):
    call_sid: str
    to_number: str

class DialoutResponse(BaseModel):
    call_sid: str
    status: str
    to_number: str

class TwimlRequest(BaseModel):
    to_number: str
    from_number: str
    name: str

async def dialout_request_from_request(request: Request) -> DialoutRequest:  
    data = await request.json()
    try:
        return DialoutRequest.model_validate(data)
    except Exception as e:
        return HTTPException(status_code=400, detail=f"Invalid request format: {str(e)}")


async def make_twilio_call(dialout_request: DialoutRequest) -> TwilioCallResult: 
    to_number = dialout_request.to_number
    from_number = dialout_request.from_number
    name = dialout_request.name

    local_url = os.getenv("LOCAL_URL")

    if not local_url:
        raise ValueError("Local url not found")
    
    twiml_url = f"{local_url}/twiml?name={name}"
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")

    if not auth_token or not account_sid:
        raise ValueError("Missing Twilio credentials")
    
    client = TwilioClient(account_sid, auth_token)
    call = client.calls.create(to=to_number, from_=from_number, url=twiml_url, method="POST")

    return TwilioCallResult(call_sid=call.sid, to_number=to_number)

async def parse_twiml_request(request: Request) -> TwimlRequest:

    data = await request.form()
    to_number = data.get("To")
    from_number = data.get("From")
    name = request.query_params.get('name')

    return TwimlRequest(to_number=to_number, from_number=from_number, name=name)

def get_websocket_url() -> str:

    local_url = os.getenv("LOCAL_URL")

    if not local_url:
        raise ValueError("Missing local url")
    
    ws_url = local_url.replace("https://", "wss://")
    return f"{ws_url}/ws"

def generate_twiml(request: TwimlRequest) -> str:

    ws_url = get_websocket_url()

    logger.debug(f"Generating TwiML with websocket url: {ws_url}")

    response = VoiceResponse()
    connect = Connect()
    stream = Stream(url=ws_url)

    stream.parameter(name="to_number", value=request.to_number)
    stream.parameter(name="from_number", value=request.from_number)
    stream.parameter(name="name", value=request.name)

    connect.append(stream)
    response.append(connect)
    response.pause(length=20)

    return str(response)