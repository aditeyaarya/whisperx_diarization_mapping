from typing import Any, Dict, List, Optional
import torch
import whisperx

def get_whisper_model(model_size: str, device: str, compute_type: str):
    torch.set_grad_enabled(False)
    try: torch.set_float32_matmul_precision("high")
    except Exception: pass
    return whisperx.load_model(model_size, device, compute_type=compute_type)

def asr_transcribe(model, input_path: str, language: Optional[str], device: str) -> Dict[str, Any]:
    with torch.inference_mode():
        return model.transcribe(
            input_path,
            language=language,
            batch_size=16 if device == "cuda" else 1
        )

def as_segments(asr_result: Any) -> List[dict]:
    if asr_result is None: return []
    if isinstance(asr_result, list): return asr_result
    if isinstance(asr_result, dict):
        for k in ("segments", "items", "result"):
            v = asr_result.get(k)
            if isinstance(v, list): return v
    return []
