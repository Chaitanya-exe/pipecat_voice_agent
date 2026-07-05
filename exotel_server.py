import os
import uvicorn
import aiohttp
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv(override=True)

async def initiate_call(client: aiohttp.ClientSession, to_number: str, from_: str, name: str = ""):

    api_key = os.getenv("EXOTEL_USERNAME")
    api_pass = os.getenv("EXOTEL_PASSWD")
    api_sid = os.getenv("EXOTEL_SID")

    if not all([api_key, api_pass, api_sid]):
        raise ValueError("Some credentials are missing")
    

    url = f"https://api.exotel.com/v1/Accounts/{api_sid}/Calls/connect?name={name}"

    data = {
        "To": to_number,
        "From": from_,
        "CallerId": from_,
        "CallType": "trans"
    }
    auth = aiohttp.BasicAuth(api_key, api_pass)

    async with client.post(url=url, data=data, auth=auth) as response:
        if response.status != 200:
            error = await response.text()

            raise Exception(f"Exotel API error ({response.status}): {error}")
        
        result = await response.text()

        call_sid = "unknown"
        print(result)
        if "<Sid>" in result:
            start = result.find("<Sid>") + 5
            end = result.find("</Sid>")

            call_sid = result[start:end]

        return {"status": "call_initiated", "call_sid": call_sid}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.session = aiohttp.ClientSession()
    yield
    await app.state.session.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
    )

@app.post("/start")
async def handle_call_request(request: Request) -> JSONResponse:
    
    print("Recieved outbound call request") 
    
    try:
        data = await request.json()

        if not data.get("dialout_settings"):
            raise HTTPException(status_code=400, detail="Missing dialout_settings in the request body")

        if not data['dialout_settings'].get("number"):
            raise HTTPException(status_code=400, detail="Missing number to call in request body")
        
        to_number = str(data['dialout_settings']['number'])
        try:
            call_result = await initiate_call(client=request.app.state.session, to_number=to_number, from_=os.getenv("EXOTEL_FROM_NUMBER"))

            call_sid = call_result.get("call_sid")

        except Exception as e:
            print("An error occured: ", e) 
            raise HTTPException(status_code=500, detail=f"Failed to initiate call: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        print("Unknown error occured: ", e)
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
    
    return JSONResponse({
        "call_sid": call_sid,
        "status":"call_initiated",
        "phone_number": to_number
    })

@app.websocket("/ws")
async def socket_endpoin(ws: WebSocket):

    await ws.accept()
    print("Websocket connection accepted for outbound call")
    try:
        from pipecat.runner.types import WebSocketRunnerArguments
        from bot import exotel_bot

        runner_args = WebSocketRunnerArguments(websocket=ws)
        runner_args.handle_sigint = False
        await exotel_bot(runner_args=runner_args)
    except Exception as e:
        print(f"Error in websocket endpoint: ",e)
        await ws.close()
    

if __name__ == '__main__':
    uvicorn.run("exotel_server:app", host='0.0.0.0', port=7860, reload=True)