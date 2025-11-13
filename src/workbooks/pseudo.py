import re
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import random

CODE_RE = re.compile(r'^[MFG]\d{3,6}$', re.IGNORECASE)
SEEDS = {"Mentor": 12345, "Founder": 67890, "Guest": 100}
PREFIX = {"Mentor": "M", "Founder": "F", "Guest": "G"}

def smart_extract_name_code(a: str, b: str | None = None) -> tuple[str, str]:
    a = (a or "").strip()
    b = (b or "").strip() if b is not None else None
    if b is not None and a and b:
        if CODE_RE.match(a) and not CODE_RE.match(b): return (b, a)
        if CODE_RE.match(b) and not CODE_RE.match(a): return (a, b)
        if CODE_RE.match(a) and CODE_RE.match(b):     return (b, a)
        if CODE_RE.match(b):                          return (a, b)
        return (a, b)
    txt = a
    if not txt: return ("", "")
    parts = txt.split()
    for i, tok in enumerate(parts):
        if CODE_RE.match(tok):
            name = " ".join(parts[:i] + parts[i+1:]).strip()
            code = tok
            return (name, code) if name else ("", code)
    if CODE_RE.match(txt): return ("", txt)
    return (txt, "")

def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
    cols_lower = {c.lower(): c for c in df.columns}
    name_col, code_col = cols_lower.get("name"), cols_lower.get("code")
    rows = []
    if name_col and code_col:
        for a, b in zip(df[name_col], df[code_col]):
            n, c = smart_extract_name_code(a, b); 
            if n or c: rows.append({"Name": n, "Code": c})
    elif len(df.columns) >= 2:
        colA, colB = df.columns[:2]
        for a, b in zip(df[colA], df[colB]):
            n, c = smart_extract_name_code(a, b); 
            if n or c: rows.append({"Name": n, "Code": c})
    else:
        only = df.columns[0]
        for a in df[only]:
            n, c = smart_extract_name_code(a, None); 
            if n or c: rows.append({"Name": n, "Code": c})
    out = pd.DataFrame(rows, columns=["Name","Code"]).fillna("")
    return out.drop_duplicates(subset=["Name","Code"], keep="first") if not out.empty else out

def load_pseudo_book(upload) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    xls = pd.ExcelFile(upload)
    sheets_lower = {name.lower(): name for name in xls.sheet_names}
    name_m = sheets_lower.get("mentors")  or sheets_lower.get("mentor")  or list(sheets_lower.values())[0]
    name_f = sheets_lower.get("founders") or sheets_lower.get("founder") or (list(sheets_lower.values())[1] if len(sheets_lower)>=2 else name_m)
    name_g = sheets_lower.get("guests")   or sheets_lower.get("guest")   or (list(sheets_lower.values())[2] if len(sheets_lower)>=3 else name_f)
    df_m = normalize_df(pd.read_excel(xls, sheet_name=name_m))
    df_f = normalize_df(pd.read_excel(xls, sheet_name=name_f))
    df_g = normalize_df(pd.read_excel(xls, sheet_name=name_g))
    return df_m, df_f, df_g

def new_rngs():
    return {"Mentor": random.Random(SEEDS["Mentor"]),
            "Founder": random.Random(SEEDS["Founder"]),
            "Guest":  random.Random(SEEDS["Guest"])}

def lookup_table(df: pd.DataFrame) -> Dict[str, str]:
    return {str(n).strip().lower(): str(c).strip() for n, c in zip(df["Name"], df["Code"]) if str(n).strip()}

def next_unique_code(category: str, existing_codes: set, rngs: Dict[str, random.Random]) -> str:
    rng = rngs[category]; prefix = PREFIX[category]
    while True:
        code = f"{prefix}{rng.randint(0, 99999)}"
        if code not in existing_codes:
            existing_codes.add(code)
            return code

def ensure_codes_for_names(names: List[str], df: pd.DataFrame, lut: Dict[str,str],
                           category: str, existing: set, rngs: Dict[str, random.Random]):
    updates = []
    for nm in [x.strip() for x in names if x.strip()]:
        key = nm.lower()
        if key in lut and lut[key]:
            updates.append((nm, lut[key], True))
        else:
            code = next_unique_code(category, existing, rngs)
            df.loc[len(df)] = {"Name": nm, "Code": code}
            lut[key] = code
            updates.append((nm, code, False))
    return df, lut, updates

def save_pseudo_working_copy(path: Path, df_m: pd.DataFrame, df_f: pd.DataFrame, df_g: pd.DataFrame) -> bytes:
    def reorder(df):
        if "Code" not in df.columns: df = df.assign(Code="")
        if "Name" not in df.columns: df = df.assign(Name="")
        return df[["Code","Name"]].sort_values("Name")
    buf = BytesIO()
    m, f, g = reorder(df_m), reorder(df_f), reorder(df_g)
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        m.to_excel(writer, sheet_name="Mentors", index=False)
        f.to_excel(writer, sheet_name="Founders", index=False)
        g.to_excel(writer, sheet_name="Guests", index=False)
    data = buf.getvalue()
    path.write_bytes(data)
    # also copy to Downloads with the exact requested filename (typo intentional)
    (Path.home() / "Downloads" / "Psuedo Codes.xlsx").write_bytes(data)
    return data
