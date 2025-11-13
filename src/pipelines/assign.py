from typing import Any, Dict, List, Optional
import whisperx

def assign_speakers_to_words(diar_raw: Any, aligned: Any) -> List[Dict[str, Any]]:
    word_level = whisperx.assign_word_speakers(diar_raw, aligned)

    words: Optional[List[Dict[str, Any]]] = None
    if isinstance(word_level, dict):
        for key in ("words","word_segments","segments","items","result"):
            cand = word_level.get(key)
            if isinstance(cand, list) and cand:
                words = cand; break
        if words is None:
            for v in word_level.values():
                if isinstance(v, list) and v:
                    words = v; break
    elif isinstance(word_level, list):
        words = word_level
    return words or []

def unique_speakers_in_words(words: List[Dict[str, Any]]) -> int:
    return len({(w.get("speaker") or "SPEAKER_00") for w in words})

def ensure_word_text(words: List[Dict[str, Any]]):
    for w in words:
        if not (isinstance(w.get("text"), str) and w["text"].strip()):
            if isinstance(w.get("word"), str) and w["word"].strip():
                w["text"] = w["word"]
