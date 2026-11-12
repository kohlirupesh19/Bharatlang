import time
from pathlib import Path
import numpy as np
from typing import Any, List, Mapping, Optional, Sequence, Tuple
from faster_whisper import WhisperModel
from faster_whisper.vad import VadOptions, get_speech_timestamps
from backend.app.services.asr.base import ASREngine, TranscriptionResult, TranscriptionSegment
from backend.app.services.asr.long_audio import AudioPiece, plan_pieces
from backend.app.core.config import settings
from backend.app.core.logging import logger

# Long-audio splitting: pauses this long or longer can end a piece; pieces get this much context.
PIECE_MIN_PAUSE_MS = 300
PIECE_PAD_SEC = 0.2


def find_speech(audio: np.ndarray, sample_rate: int, max_piece_s: float) -> Sequence[Mapping[str, int]]:
    """Silero VAD speech regions (sample indices); regions longer than max_piece_s are split."""
    options = VadOptions(min_silence_duration_ms=PIECE_MIN_PAUSE_MS, max_speech_duration_s=max_piece_s)
    return get_speech_timestamps(audio, options, sampling_rate=sample_rate)


MARATHI_PROMPT_BIAS = "नमस्कार, मला शेतकरी कर्जमाफी, पीक विमा आणि शासकीय अनुदान योजनांबद्दल माहिती हवी आहे."

class FasterWhisperEngine(ASREngine):
    """
    Faster-Whisper ASR engine powered by CTranslate2.

    Stock models are named by size ("small"); fine-tuned models load from a local CT2
    directory (`model_path`). Fine-tuned Marathi models were benchmarked without the
    prompt bias and without conditioning on previous text, so they are decoded that way
    (`prompt_bias=False`, `condition_on_previous_text=False`) to keep the measured WER valid.
    """

    def __init__(
        self,
        model_size: str = "small",
        compute_type: str = "int8",
        model_path: Optional[str] = None,
        display_name: Optional[str] = None,
        prompt_bias: bool = True,
        condition_on_previous_text: bool = True,
    ):
        self.model_size = model_size
        self.compute_type = compute_type
        self.model_path = model_path
        self.display_name = display_name or f"faster-whisper-{model_size}"
        self.prompt_bias = prompt_bias
        self.condition_on_previous_text = condition_on_previous_text
        self.model: Optional[WhisperModel] = None
        self._is_loaded = False

    def load_model(self) -> None:
        if self._is_loaded and self.model is not None:
            return

        if self.model_path is not None and not Path(self.model_path).is_dir():
            raise FileNotFoundError(
                f"ASR model directory not found: {self.model_path}. "
                "Convert the model with scripts/convert_whisper.py or pick another ASR_ACTIVE_MODEL."
            )
        source = self.model_path or self.model_size
        device = settings.WHISPER_DEVICE
        logger.info(f"Loading ASR model '{self.display_name}' from '{source}' (device={device}, compute_type={self.compute_type})...")
        t0 = time.time()
        self.model = WhisperModel(
            source,
            device=device,
            compute_type=self.compute_type,
            cpu_threads=4
        )
        self._is_loaded = True
        logger.info(f"ASR model '{self.display_name}' loaded in {time.time() - t0:.2f}s")

    def unload_model(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None
            self._is_loaded = False
            logger.info(f"ASR model '{self.display_name}' unloaded from memory.")

    def is_loaded(self) -> bool:
        return self._is_loaded and self.model is not None

    def _decode(self, audio: np.ndarray, lang_code: str, initial_prompt: Optional[str]) -> Tuple[list, Any]:
        segments, info = self.model.transcribe(
            audio,
            language=lang_code,
            initial_prompt=initial_prompt,
            condition_on_previous_text=self.condition_on_previous_text,
            beam_size=5,
            temperature=0.0,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=400)
        )
        return list(segments), info

    def _plan(self, audio: np.ndarray, sample_rate: int) -> Tuple[AudioPiece, ...]:
        """Pause-delimited pieces for audio longer than one safe decoding window, else none."""
        max_s = settings.ASR_MAX_PIECE_SEC
        if len(audio) / sample_rate <= max_s:
            return ()
        pieces = plan_pieces(find_speech(audio, sample_rate, max_s), total_samples=len(audio),
                             sample_rate=sample_rate, max_piece_s=max_s, pad_s=PIECE_PAD_SEC)
        return pieces if len(pieces) > 1 else ()

    def transcribe(
        self,
        audio_array: np.ndarray,
        sample_rate: int = 16000,
        language: str = "mr",
        audio_identifier: str = "audio_sample"
    ) -> TranscriptionResult:
        if not self.is_loaded():
            self.load_model()

        start_time = time.time()

        # Target language mapping
        lang_code = "mr" if language in ["mr", "marathi", "mr-varhadi", "varhadi"] else ("hi" if language == "hi" else "en")
        initial_prompt = MARATHI_PROMPT_BIAS if (lang_code == "mr" and self.prompt_bias) else None

        try:
            # Long audio is decoded piece by piece (services/asr/long_audio.py) so the
            # 448-token window cannot cut off the end of the question.
            pieces = self._plan(audio_array, sample_rate)
            if pieces:
                logger.info(f"Decoding {len(audio_array) / sample_rate:.1f}s of audio in {len(pieces)} pieces")
                decoded = [(p.start / sample_rate, *self._decode(audio_array[p.start:p.end], lang_code, initial_prompt))
                           for p in pieces]
            else:
                decoded = [(0.0, *self._decode(audio_array, lang_code, initial_prompt))]
            info = decoded[0][2]

            segments_list: List[TranscriptionSegment] = []
            text_parts = []
            confidence_scores = []

            for offset, segments, _ in decoded:
                for seg in segments:
                    # Calibrated confidence from avg_logprob
                    # avg_logprob is log(p); exp(avg_logprob) is approximate sequence probability in [0, 1]
                    conf = float(np.clip(np.exp(seg.avg_logprob), 0.0, 1.0))
                    confidence_scores.append(conf)

                    text_clean = seg.text.strip()
                    text_parts.append(text_clean)

                    segments_list.append(TranscriptionSegment(
                        id=len(segments_list),
                        start=round(float(seg.start) + offset, 2),
                        end=round(float(seg.end) + offset, 2),
                        text=text_clean,
                        confidence=round(conf, 3),
                        avg_logprob=round(float(seg.avg_logprob), 3)
                    ))

            recognized_text = " ".join(text_parts).strip()
            duration = time.time() - start_time

            overall_confidence = float(np.mean(confidence_scores)) if confidence_scores else 0.0
            is_uncertain = overall_confidence < 0.50 or len(recognized_text) == 0

            warning_message = None
            if is_uncertain:
                if len(recognized_text) == 0:
                    warning_message = "No audible speech was recognized. Please check your microphone or speak louder."
                else:
                    warning_message = "Recognition quality is uncertain (low acoustic confidence). Please review and correct the transcript below."

            return TranscriptionResult(
                audio_identifier=audio_identifier,
                selected_language=language,
                detected_language=info.language or lang_code,
                recognized_text=recognized_text,
                segments=segments_list,
                model_name=self.display_name,
                model_version="1.2.1",
                processing_duration_sec=round(duration, 3),
                overall_confidence=round(overall_confidence, 3) if confidence_scores else None,
                is_uncertain=is_uncertain,
                warning_message=warning_message,
                metadata={
                    "language_probability": round(float(info.language_probability), 3) if hasattr(info, 'language_probability') else None,
                    "compression_ratio": round(float(info.compression_ratio), 3) if hasattr(info, 'compression_ratio') else None,
                    "compute_type": self.compute_type,
                    "pieces": max(len(pieces), 1)
                }
            )
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            raise
