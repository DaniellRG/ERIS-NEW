"""Pipecat voice pipeline for Eris.

Provides a modern STT→LLM→TTS pipeline with turn detection, VAD, and interruptions.
Can be used as an alternative to the manual audio loop in main.py.

Usage:
    from core.pipecat_pipeline import ErisPipecatPipeline
    pipeline = ErisPipecatPipeline()
    await pipeline.run()
"""

import asyncio
import os
from pathlib import Path
from core.platform import safe_print

BASE_DIR = Path(__file__).parent.parent


class ErisPipecatPipeline:
    """Pipecat-based voice pipeline for Eris."""

    def __init__(self, stt_model="tiny", tts_voice=None, llm_model="llama3.2"):
        self.stt_model = stt_model
        self.tts_voice = tts_voice or "es_ES-sharvard-medium"
        self.llm_model = llm_model
        self._running = False

    async def create_pipeline(self):
        """Create the Pipecat pipeline components."""
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams
        from pipecat.services.whisper.stt import WhisperSTTService
        from pipecat.services.piper.tts import PiperTTSService
        from pipecat.services.openai.llm import OpenAILLMService
        from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair

        # Audio transport (local mic + speaker)
        transport = LocalAudioTransport(
            LocalAudioTransportParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                vad_enabled=True,
            )
        )

        # STT (Whisper)
        stt = WhisperSTTService(
            model=self.stt_model,
            device="cpu",
            compute_type="int8",
        )

        # LLM (via Ollama OpenAI-compatible API)
        llm = OpenAILLMService(
            api_key="ollama",
            base_url="http://localhost:11434/v1",
            model=self.llm_model,
        )

        # TTS (Piper)
        tts = PiperTTSService(
            voice_id=self.tts_voice,
        )

        # Context
        from pipecat.processors.aggregators.llm_context import LLMContext
        context = LLMContext()
        context_aggregator = LLMContextAggregatorPair(context)

        # Build pipeline
        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ])

        return pipeline, transport

    async def run(self):
        """Run the Pipecat pipeline."""
        try:
            pipeline, transport = await self.create_pipeline()
            from pipecat.pipeline.runner import PipelineRunner
            from pipecat.pipeline.task import PipelineTask

            task = PipelineTask(pipeline)
            runner = PipelineRunner()
            self._running = True
            await runner.run(task)
        except Exception as e:
            safe_print(f"[PIPECAT] Error: {e}")
            self._running = False

    def stop(self):
        """Stop the pipeline."""
        self._running = False


async def test_pipecat():
    """Test Pipecat pipeline creation."""
    try:
        pipeline = ErisPipecatPipeline()
        p, t = await pipeline.create_pipeline()
        print("✅ Pipecat pipeline created successfully")
        return True
    except Exception as e:
        print(f"❌ Pipecat pipeline error: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_pipecat())
