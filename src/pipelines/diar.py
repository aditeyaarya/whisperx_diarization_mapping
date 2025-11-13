from typing import Any
from whisperx.diarize import DiarizationPipeline

def get_diar_pipeline(device: str, hf_token: str):
    try:
        return DiarizationPipeline(use_auth_token=hf_token, device=device)
    except TypeError:
        return DiarizationPipeline(use_auth_token=hf_token, device=device)

def run_diarization(pipe: Any, input_path: str):
    return pipe(input_path)
