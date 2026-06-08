import os
from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.services.ollama.llm import OLLamaLLMService
from pipecat.services.whisper.stt import WhisperSTTService, Model
from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.transcriptions.language import Language
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.workers.runner import WorkerRunner
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport, FastAPIWebsocketParams
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.runner.utils import parse_telephony_websocket 

with open("system_prompt.txt", "r") as file:
    prompt = file.read()

transport_params = {
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True
    ),
}

async def run_bot(transport: BaseTransport, handle_sigint: bool):
    runner = WorkerRunner(handle_sigint=handle_sigint)

    tts = KokoroTTSService(
        settings=KokoroTTSService.Settings(voice='hf_alpha', language=Language.HI, extra={"speed": 1.3})
    )

    stt = WhisperSTTService(
        compute_type="int8",
        device="auto",
        model=Model.SMALL,
    )

    llm = OLLamaLLMService(settings=OLLamaLLMService.Settings(
        model="qwen2.5:1.5b",
        temperature=0,
        system_instruction=prompt
    ))

    context = LLMContext()

    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer())
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator
        ]
    )

    agent = PipelineWorker(
        pipeline,
        name="assistant",
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            enable_metrics=True,
            enable_usage_metrics=True
        )
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info("Starting outbound call conversation")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Outbound call ended")
        await agent.cancel()
    
    await runner.add_workers(agent)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Main entry point for the Voice Agent"""
    
    transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
    logger.info(f"Auto-detected transport type: {transport_type}")

    body_data = call_data.get("body", {})
    to_number = body_data.get("to_number")
    from_number = body_data.get("from_number")

    logger.info(f"Call Metadat: To - {to_number}    From - {from_number}")

    serializer = TwilioFrameSerializer(
        account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        stream_sid=call_data['stream_id'],
        call_sid=call_data['call_id']
    )

    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            serializer=serializer,
            add_wav_header=False
        )
    )

    handle_sigint = runner_args.handle_sigint

    await run_bot(transport=transport, handle_sigint=handle_sigint)
