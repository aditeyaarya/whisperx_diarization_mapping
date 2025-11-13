from typing import Any, Tuple
import whisperx

def get_align_model(language_code: str, device: str) -> Tuple[Any, Any]:
    return whisperx.load_align_model(language_code=language_code, device=device)

def align_segments(segments, align_model, metadata, input_path: str, device: str):
    return whisperx.align(segments, align_model, metadata, input_path, device, return_char_alignments=False)
