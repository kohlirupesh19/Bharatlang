import os
import subprocess
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any
from backend.app.core.config import settings
from backend.app.core.logging import logger

def preprocess_audio_to_numpy(
    input_audio_path: str,
    target_sample_rate: int = 16000,
    normalize_volume: bool = True
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Decodes and resamples any audio format (WAV, MP3, WEBM, OGG, M4A)
    into a mono float32 numpy array at target_sample_rate (default 16000 Hz)
    using ffmpeg.
    
    Performs:
    - Audio format decoding
    - Strict mono downmixing
    - True 16kHz resampling
    - Volume normalization (peak/RMS)
    - Silence & energy metrics calculation
    """
    if not os.path.exists(input_audio_path):
        raise FileNotFoundError(f"Audio file not found: {input_audio_path}")

    # Use ffmpeg to stream decoded raw float32 pcm mono audio at target_sample_rate
    cmd = [
        settings.FFMPEG_PATH,
        "-nostdin",
        "-threads", "1",
        "-i", str(input_audio_path),
        "-f", "f32le",
        "-acodec", "pcm_f32le",
        "-ac", "1",
        "-ar", str(target_sample_rate),
        "-"
    ]

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        raw_pcm, stderr_output = process.communicate()
        if process.returncode != 0:
            err = stderr_output.decode('utf-8', errors='ignore')
            raise RuntimeError(f"FFmpeg decoding failed (code {process.returncode}): {err}")
    except Exception as e:
        logger.error(f"Error executing ffmpeg on {input_audio_path}: {e}")
        raise

    if len(raw_pcm) == 0:
        raise ValueError("Decoded audio stream is empty.")

    audio_array = np.frombuffer(raw_pcm, dtype=np.float32)

    # Compute audio duration and statistics
    duration_sec = len(audio_array) / float(target_sample_rate)
    max_peak = float(np.max(np.abs(audio_array))) if len(audio_array) > 0 else 0.0
    rms_energy = float(np.sqrt(np.mean(audio_array**2))) if len(audio_array) > 0 else 0.0

    # Volume normalization: scale to target peak of 0.95 without clipping
    if normalize_volume and max_peak > 1e-4:
        gain = 0.95 / max_peak
        # Cap excessive gain amplification on silent recordings
        gain = min(gain, 10.0)
        audio_array = audio_array * gain
        max_peak = float(np.max(np.abs(audio_array)))
        rms_energy = float(np.sqrt(np.mean(audio_array**2)))

    # Basic Voice Activity / Silence Detection based on frame energy
    frame_size = int(target_sample_rate * 0.03)  # 30ms frames
    num_frames = len(audio_array) // frame_size
    silence_frames = 0
    energy_threshold = 0.015

    if num_frames > 0:
        for i in range(num_frames):
            frame = audio_array[i * frame_size : (i + 1) * frame_size]
            frame_rms = np.sqrt(np.mean(frame**2))
            if frame_rms < energy_threshold:
                silence_frames += 1
        silence_ratio = silence_frames / num_frames
    else:
        silence_ratio = 1.0

    metadata = {
        "duration_sec": round(duration_sec, 3),
        "sample_rate": target_sample_rate,
        "samples": len(audio_array),
        "max_peak": round(max_peak, 4),
        "rms_energy": round(rms_energy, 4),
        "silence_ratio": round(silence_ratio, 3),
        "is_silent": bool(silence_ratio > 0.95 or rms_energy < 0.005)
    }

    return audio_array, metadata

def save_wav_audio(audio_array: np.ndarray, output_path: str, sample_rate: int = 16000) -> str:
    """Save float32 audio array to a standard 16-bit PCM WAV file."""
    import soundfile as sf
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio_array, sample_rate, subtype="PCM_16")
    return output_path

