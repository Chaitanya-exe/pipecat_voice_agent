import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse, HTMLResponse
from loguru import logger
from server_utils import (
    DialoutResponse,
    generate_twiml,
    dialout_request_from_request,
    make_twilio_call,
    parse_twiml_request
)

load_dotenv(override=True)

app = FastAPI(description="An orchestraion server for Pipecat Voice Agent")

@app.post("/dialout", response_model=DialoutResponse)
async def handle_dialout_request(request: Request) -> DialoutResponse:

    logger.info("Recieved outbound call request")

    dialout_request = await dialout_request_from_request(request=request)

    call = await make_twilio_call(dialout_request=dialout_request)

    return DialoutResponse(
        call_sid=call.call_sid,
        status="call_initiated",
        to_number=call.to_number
    )

@app.post("/twiml")
async def get_twiml(request: Request) -> HTMLResponse:

    logger.info("Serving TwiML for outbout call")
    twiml_request = await parse_twiml_request(request=request)
    twiml_content = generate_twiml(request=twiml_request)

    return HTMLResponse(content=twiml_content, media_type="application/xml")

@app.websocket("/ws")
async def handle_websocket(socket: WebSocket):
    from bot import bot
    from pipecat.runner.types import WebSocketRunnerArguments

    await socket.accept()
    logger.info("Socket connection accepted for the outbound call")

    try:
        runner_args = WebSocketRunnerArguments(websocket=socket)
        await bot(runner_args=runner_args)
    except Exception as e:
        logger.error(f"Error on websocket endpoint: {str(e)}") 
        await socket.close()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    logger.info(f"Starting outbound call agent on port: {port}")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)