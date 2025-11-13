from typing import List, Dict, Any

def merge_words_to_turns(words: List[Dict[str, Any]], gap: float = 0.6) -> List[Dict[str, Any]]:
    turns: List[Dict[str, Any]] = []
    if not words: return turns
    cur_spk, cur_start, cur_end, cur_txt = None, None, None, []
    for w in words:
        spk = w.get("speaker") or "SPEAKER_00"
        ws = float(w.get("start", 0.0) or 0.0)
        we = float(w.get("end", ws) or ws)
        tx = (w.get("text") or w.get("word") or "").strip()
        if cur_spk is None:
            cur_spk, cur_start, cur_end, cur_txt = spk, ws, we, ([tx] if tx else [])
            continue
        if spk != cur_spk or (ws - (cur_end or ws)) > gap:
            turns.append({"speaker": cur_spk, "start": cur_start, "end": cur_end, "text": " ".join(cur_txt).strip()})
            cur_spk, cur_start, cur_end, cur_txt = spk, ws, we, ([tx] if tx else [])
        else:
            cur_end = max(cur_end or we, we)
            if tx: cur_txt.append(tx)
    if cur_spk is not None:
        turns.append({"speaker": cur_spk, "start": cur_start, "end": cur_end, "text": " ".join(cur_txt).strip()})
    return turns

def turns_to_txt(turns: List[Dict[str, Any]]) -> str:
    lines = []
    for t in turns:
        s = f"{int(t['start']//60):02d}:{t['start']%60:05.2f}"
        e = f"{int(t['end']//60):02d}:{t['end']%60:05.2f}"
        lines.append(f"[{s}-{e}] {t.get('speaker','SPEAKER_00')}: {t.get('text','')}")
    return "\n".join(lines)
