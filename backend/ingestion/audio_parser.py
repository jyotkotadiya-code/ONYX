import wave
from pathlib import Path
from typing import Any
from backend.core.config import settings
from backend.core.logging_config import error_logger, ingestion_logger
from backend.core.models import ParsedBlock


class LocalAudioParser:
    """
    Phase 2 Local Audio Ingestion (MP3, WAV, M4A).
    Uses local Whisper (`faster-whisper` or `openai-whisper`) on CPU when AUDIO_ENABLED=true.
    Produces timestamp-aware transcript segments.
    """

    def __init__(self) -> None:
        self._whisper_model = None

    def get_status(self) -> dict[str, Any]:
        if not settings.AUDIO_ENABLED:
            return {
                "status": "disabled",
                "engine": "Whisper (Disabled in .env)",
                "note": "Set AUDIO_ENABLED=true in .env to enable local Whisper transcription.",
            }
        try:
            import faster_whisper  # noqa: F401

            return {
                "status": "available",
                "engine": f"faster-whisper ({settings.WHISPER_MODEL_SIZE}, CPU int8)",
            }
        except ImportError:
            try:
                import whisper  # noqa: F401

                return {
                    "status": "available",
                    "engine": f"openai-whisper ({settings.WHISPER_MODEL_SIZE}, CPU)",
                }
            except ImportError:
                return {
                    "status": "optional_not_installed",
                    "engine": "Whisper (Not Installed)",
                    "suggested_action": "Run `pip install faster-whisper` and set AUDIO_ENABLED=true",
                }

    def _get_wav_duration(self, file_path: Path) -> float:
        try:
            if file_path.suffix.lower() == ".wav":
                with wave.open(str(file_path), "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    if rate > 0:
                        return round(frames / float(rate), 2)
        except Exception:
            pass
        return 0.0

    def parse_audio(self, file_path: Path) -> tuple[list[ParsedBlock], dict[str, Any]]:
        duration = self._get_wav_duration(file_path)

        if not settings.AUDIO_ENABLED:
            raise RuntimeError(
                "Audio ingestion is currently disabled (AUDIO_ENABLED=false). "
                "Suggested action: Set AUDIO_ENABLED=true in .env and install faster-whisper (`pip install faster-whisper`)."
            )

        blocks: list[ParsedBlock] = []
        try:
            from faster_whisper import WhisperModel

            model = WhisperModel(
                settings.WHISPER_MODEL_SIZE,
                device="cpu",
                compute_type="int8",
                download_root=str(settings.resolve_path(settings.MODELS_DIR)),
            )
            segments, info = model.transcribe(str(file_path), beam_size=5)
            duration = round(getattr(info, "duration", duration) or duration, 2)

            for idx, seg in enumerate(segments, start=1):
                start_s = round(float(seg.start), 2)
                end_s = round(float(seg.end), 2)
                txt = seg.text.strip()
                if txt:
                    blocks.append(
                        ParsedBlock(
                            text=f"[{start_s:.1f}s - {end_s:.1f}s] {txt}",
                            modality="audio",
                            page_number=idx,
                            section_title=f"Audio Timestamp {start_s:.1f}s - {end_s:.1f}s",
                            timestamp_start=start_s,
                            timestamp_end=end_s,
                            extra_metadata={
                                "filename": file_path.name,
                                "duration": duration,
                                "timestamp": f"{start_s:.1f}s-{end_s:.1f}s",
                            },
                        )
                    )
        except ImportError:
            raise RuntimeError(
                "Local Whisper package (`faster-whisper`) is not installed. "
                "Suggested action: Install with `pip install faster-whisper`."
            )
        except Exception as e:
            error_logger.error(f"Audio transcription failed for {file_path.name}: {e}")
            raise RuntimeError(f"Local Whisper transcription failed: {e}")

        meta = {
            "filename": file_path.name,
            "duration_seconds": duration,
            "segments_count": len(blocks),
            "page_count": max(1, len(blocks)),
        }
        ingestion_logger.info(
            f"Transcribed Audio '{file_path.name}' ({duration}s) into {len(blocks)} timestamped blocks."
        )
        return blocks, meta


audio_parser = LocalAudioParser()
