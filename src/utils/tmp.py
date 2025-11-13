from pathlib import Path

def save_tmp(file) -> str:
    tmp = Path(".streamlit_tmp"); tmp.mkdir(exist_ok=True)
    p = tmp / file.name
    with open(p, "wb") as f: f.write(file.getbuffer())
    return str(p)

def fix_tqdm():
    try:
        import importlib, tqdm as tq, tqdm.auto as tqa
        if not hasattr(tq.tqdm, "_lock"):
            tq.tqdm = tqa.tqdm
        if hasattr(tq, "_instances"):
            try: tq._instances.clear()
            except Exception: pass
        if not hasattr(tq.tqdm, "_lock"):
            importlib.reload(tq); importlib.reload(tqa); tq.tqdm = tqa.tqdm
    except Exception:
        pass
