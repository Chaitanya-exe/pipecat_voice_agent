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
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport, TransportParams

with open("system_prompt.txt", "r") as file:
    prompt = file.read()

transport_params = {
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True
    ),
}

async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    runner = WorkerRunner(handle_sigint=runner_args.handle_sigint)

    tts = KokoroTTSService(
        settings=KokoroTTSService.Settings(voice='hf_alpha', language=Language.HI)
    )

    stt = WhisperSTTService(
        compute_type="int8",
        device="auto",
        model=Model.SMALL,
    )

    llm = OLLamaLLMService(settings=OLLamaLLMService.Settings(
        model="gemma4:e2b",
        temperature=0.3,
        system_instruction=prompt
    ))

    context = LLMContext()

    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer())
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            aggregators.user(),
            llm,
            tts,
            transport.output(),
            aggregators.assistant()
        ]
    )

    agent = PipelineWorker(
        pipeline,
        name="assistant",
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True)
    )

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await runner.cancel()
    
    await runner.add_workers(agent)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    transport = await create_transport(transport_params=transport_params, runner_args=runner_args)
    await run_bot(transport=transport, runner_args=runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
