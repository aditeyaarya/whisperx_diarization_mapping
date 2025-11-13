import io
import re
import csv
import json
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd

from src.ui.theme import BOARDROOM_CSS, inject_theme
from src.utils.tmp import save_tmp, fix_tqdm
from src.utils.turns import merge_words_to_turns, turns_to_txt
from src.pipelines.asr import get_whisper_model, asr_transcribe, as_segments
from src.pipelines.align import get_align_model, align_segments
from src.pipelines.diar import get_diar_pipeline, run_diarization
from src.pipelines.assign import assign_speakers_to_words, unique_speakers_in_words, ensure_word_text
from src.workbooks.pseudo import (
    load_pseudo_book, save_pseudo_working_copy, new_rngs, lookup_table,
    ensure_codes_for_names
)
from src.workbooks.mapping import append_mapping_to_excel

st.set_page_config(
    page_title="Transcription, Diarization and Speaker Mapping Tool",
    page_icon="🏛️",
    layout="centered"
)
inject_theme(BOARDROOM_CSS)
fix_tqdm()

# ---------- helpers local ----------
def save_three_outputs_locally(out_dir: Path, json_bytes: bytes, csv_bytes: bytes, txt_str: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "words.json").write_bytes(json_bytes)
    (out_dir / "turns.csv").write_bytes(csv_bytes)
    (out_dir / "transcript.txt").write_text(txt_str, encoding="utf-8")

# ---------- caching ----------
@st.cache_resource(show_spinner=False)
def cache_whisper_model(model_size: str, device: str, compute_type: str):
    return get_whisper_model(model_size, device, compute_type)

@st.cache_resource(show_spinner=False)
def cache_align_model(language_code: str, device: str):
    return get_align_model(language_code, device)

@st.cache_resource(show_spinner=False)
def cache_diar_pipeline(device: str, hf_token: str):
    return get_diar_pipeline(device, hf_token)

# ---------- UI ----------
st.title("🏛️ Transcription, Diarization and Speaker Mapping Tool")

with st.sidebar:
    st.header("Transcription")
    MODEL_SIZE = st.selectbox("Whisper model", ["tiny","base","small","medium","large-v2","large-v3"], index=2)
    LANGUAGE   = st.text_input("Language (blank = auto)", value="")
    DEVICE     = st.selectbox("Device (ASR/Align)", ["cuda","cpu","mps"], index=1)

    st.header("Diarization (pyannote)")
    HF_TOKEN   = st.text_input("Hugging Face token (required)", value="", type="password")
    DIAR_DEVICE = st.selectbox("Diarization device (recommended: cpu)", ["cpu","cuda","mps"], index=0)

    st.header("System")
    FFMPEG_PATH = st.text_input("FFmpeg folder (optional, added to PATH)", value="")
    SAVE_LOCAL  = st.checkbox("Also save to Desktop/<audio>_transcription and <audio>_final", value=False)

uploaded = st.file_uploader("Upload audio/video", type=["mp3","wav","m4a","flac","mp4","mov"])
run_btn  = st.button("Run")

with st.expander("Environment info"):
    import sys, torch, whisperx
    st.write({
        "python": sys.version,
        "exe": sys.executable,
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "mps_available": getattr(torch.backends,"mps",None) and torch.backends.mps.is_available(),
        "whisperx": getattr(whisperx, "__version__", "unknown"),
    })

preview = st.empty()

# ---------- session state ----------
if "pipeline_ready" not in st.session_state:
    st.session_state.pipeline_ready = False
for k in ("words","turns","audio_name","out_dir"):
    if k not in st.session_state:
        st.session_state[k] = None

if "pseudo_state" not in st.session_state:
    st.session_state.pseudo_state = {
        "loaded": False,
        "dfs": None,        # (df_m, df_f, df_g) normalized Name, Code
        "rngs": None,
        "workbook_path": "",
    }

# ---------------------- STEP 1: ASR + ALIGN + DIAR + ASSIGN ----------------------
if run_btn:
    import os, torch
    if not uploaded:
        st.error("No file uploaded."); st.stop()
    if not HF_TOKEN or not HF_TOKEN.strip():
        st.error("Hugging Face token is required for diarization."); st.stop()
    if FFMPEG_PATH.strip():
        os.environ["PATH"] = FFMPEG_PATH.strip() + os.pathsep + os.environ.get("PATH","")

    input_path = save_tmp(uploaded)
    audio_name = Path(uploaded.name).stem
    out_dir = Path.home() / "Desktop" / f"{audio_name}_transcription"
    Path(".streamlit_tmp").mkdir(exist_ok=True)

    # Transcribe
    st.info("Transcribing…")
    try:
        compute_type = "float16" if DEVICE == "cuda" else "float32"
        model = cache_whisper_model(MODEL_SIZE, DEVICE, compute_type)
        lang_arg = None if (not LANGUAGE or not LANGUAGE.strip()) else LANGUAGE.strip()
        asr_result = asr_transcribe(model, input_path, language=lang_arg, device=DEVICE)
        segments = as_segments(asr_result)
        if not segments:
            raise RuntimeError("No segments returned by Whisper.")
    except Exception as e:
        st.error(f"❌ Transcription failed: {e}"); st.stop()

    # Align
    st.info("Aligning (word timings)…")
    try:
        detected_lang = asr_result.get("language") if isinstance(asr_result, dict) else None
        lang_code = (lang_arg or detected_lang or "en")
        align_model, metadata = cache_align_model(lang_code, DEVICE)
        aligned = align_segments(segments, align_model, metadata, input_path, DEVICE)
    except Exception as e:
        st.error(f"❌ Alignment failed: {e}"); st.stop()

    # Diarize
    st.info("Diarizing…")
    try:
        pipe = cache_diar_pipeline(DIAR_DEVICE, HF_TOKEN.strip())
        diar_raw = run_diarization(pipe, input_path)
    except Exception as e:
        st.error(f"❌ Diarization failed: {e}"); st.stop()

    # Assign speakers to words
    st.info("Assigning speakers to words…")
    try:
        words = assign_speakers_to_words(diar_raw, aligned)
        if not words:
            st.error("Speaker assignment returned empty content. Aborting (strict)."); st.stop()
        if unique_speakers_in_words(words) < 2:
            st.error("Diarization succeeded but <2 unique speakers after assignment. Aborting (strict)."); st.stop()
        ensure_word_text(words)
    except Exception as e:
        st.error(f"❌ Speaker assignment failed: {e}"); st.stop()

    # Build turns for preview
    turns = merge_words_to_turns(words, gap=0.6)
    preview.subheader("Transcript preview (by turn)")
    preview.text_area("Text", value="\n".join(turns_to_txt([t]).splitlines()), height=300, disabled=True)

    # Persist
    st.session_state.pipeline_ready = True
    st.session_state.words = words
    st.session_state.turns = turns
    st.session_state.audio_name = audio_name
    st.session_state.out_dir = out_dir

    st.success("Step 1 complete. Proceed to the downloads below or to the Pseudo Codes section.")

# ---------------------- OPTIONAL DOWNLOADS (ONLY 3 FILES) ----------------------
if st.session_state.pipeline_ready:
    st.markdown("---")
    st.subheader("Optional downloads")

    words: List[Dict[str, Any]] = st.session_state.words
    turns: List[Dict[str, Any]] = st.session_state.turns
    audio_name: str = st.session_state.audio_name
    out_dir: Path = st.session_state.out_dir

    # words.json
    json_words_bytes = json.dumps(words, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        f"⬇️ {audio_name}_words.json",
        data=json_words_bytes,
        file_name=f"{audio_name}_words.json",
        mime="application/json",
        key="dl_json_words"
    )

    # turns.csv
    csv_buf = io.StringIO()
    writer = csv.DictWriter(csv_buf, fieldnames=["speaker","start","end","text"])
    writer.writeheader()
    for t in turns:
        writer.writerow({
            "speaker": t["speaker"],
            "start": t["start"],
            "end": t["end"],
            "text": (t["text"] or "").replace("\n"," ")
        })
    csv_bytes = csv_buf.getvalue().encode("utf-8")
    st.download_button(
        f"⬇️ {audio_name}_turns.csv",
        data=csv_bytes,
        file_name=f"{audio_name}_turns.csv",
        mime="text/csv",
        key="dl_turns_csv"
    )

    # transcript.txt
    txt_str = turns_to_txt(turns)
    st.download_button(
        f"⬇️ {audio_name}.txt",
        data=txt_str.encode("utf-8"),
        file_name=f"{audio_name}.txt",
        mime="text/plain",
        key="dl_transcript_txt"
    )

    # SAVE_LOCAL writes ONLY these three
    if st.sidebar.checkbox("Confirm SAVE_LOCAL now", value=False, key="save_local_now"):
        save_three_outputs_locally(out_dir, json_words_bytes, csv_bytes, txt_str)
        st.success(f"Saved to: {out_dir} (words.json, turns.csv, transcript.txt)")

# ---------------------- STEP 2: PSEUDO-CODE WORKBOOK ----------------------
if st.session_state.pipeline_ready:
    st.markdown("---")
    st.header("🔐 Speaker Pseudo Codes (Mentors / Founders / Guests)")

    audio_name = st.session_state.audio_name
    work_dir = Path(".streamlit_tmp"); work_dir.mkdir(exist_ok=True)

    st.markdown(
        "Upload your **Pseudo Code Excel** with three sheets: **Mentors**, **Founders**, **Guests**.\n\n"
        "- Each sheet can be `Name|Code`, `Code|Name`, or single-cell mixes like `Johannes B M1332`.\n"
        "- We reuse existing codes; new codes are generated **deterministically** only when needed.\n"
        "- Seeds fixed: Mentor=12345, Founder=67890, Guest=100.\n"
        "- A working copy is saved as `~/Downloads/Psuedo Codes.xlsx` (intentional spelling)."
    )

    pseudo_book = st.file_uploader("Upload Pseudo Code Workbook (.xlsx)", type=["xlsx"], key="pseudo_xlsx")

    if pseudo_book and not st.session_state.pseudo_state["loaded"]:
        try:
            df_m, df_f, df_g = load_pseudo_book(pseudo_book)
        except Exception as e:
            st.error(f"Could not read workbook: {e}"); st.stop()
        st.session_state.pseudo_state["dfs"] = (df_m, df_f, df_g)
        st.session_state.pseudo_state["rngs"] = new_rngs()
        work_path = work_dir / f"{audio_name}_pseudo_codes_working.xlsx"
        save_pseudo_working_copy(work_path, df_m, df_f, df_g)
        st.session_state.pseudo_state["workbook_path"] = str(work_path)
        st.session_state.pseudo_state["loaded"] = True
        st.success(f"Loaded pseudo-code workbook. Working copy at: {work_path} (also saved to Downloads as 'Psuedo Codes.xlsx')")

    mentors_input  = st.text_input("Mentor name(s), comma-separated", value="", key="pc_mentors")
    founders_input = st.text_input("Founder name(s), comma-separated", value="", key="pc_founders")
    guests_input   = st.text_input("Guest name(s), comma-separated", value="", key="pc_guests")

    if st.button("Apply & Save Codes", key="pc_apply"):
        if not st.session_state.pseudo_state["loaded"]:
            st.error("Please upload the Pseudo Code workbook (.xlsx) above."); st.stop()

        df_m, df_f, df_g = st.session_state.pseudo_state["dfs"]
        rngs = st.session_state.pseudo_state["rngs"]

        lut_m, lut_f, lut_g = lookup_table(df_m), lookup_table(df_f), lookup_table(df_g)
        existing_m = {c for c in df_m["Code"] if isinstance(c, str) and c}
        existing_f = {c for c in df_f["Code"] if isinstance(c, str) and c}
        existing_g = {c for c in df_g["Code"] if isinstance(c, str) and c}

        mentors  = [x.strip() for x in mentors_input.split(",") if x.strip()]
        founders = [x.strip() for x in founders_input.split(",") if x.strip()]
        guests   = [x.strip() for x in guests_input.split(",") if x.strip()]

        df_m, lut_m, upd_m = ensure_codes_for_names(mentors,  df_m, lut_m, "Mentor",  existing_m, rngs)
        df_f, lut_f, upd_f = ensure_codes_for_names(founders, df_f, lut_f, "Founder", existing_f, rngs)
        df_g, lut_g, upd_g = ensure_codes_for_names(guests,   df_g, lut_g, "Guest",   existing_g, rngs)

        st.session_state.pseudo_state["dfs"] = (df_m, df_f, df_g)

        rows = [{"Category":"Mentor","Name":n,"Code":c,"Existing?":"Yes" if ex else "No"} for n,c,ex in upd_m] + \
               [{"Category":"Founder","Name":n,"Code":c,"Existing?":"Yes" if ex else "No"} for n,c,ex in upd_f] + \
               [{"Category":"Guest","Name":n,"Code":c,"Existing?":"Yes" if ex else "No"} for n,c,ex in upd_g]
        if rows:
            st.subheader("Pseudo Code Assignments (this apply)")
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No names entered; nothing to update.")

        work_path = Path(st.session_state.pseudo_state["workbook_path"])
        out_bytes = save_pseudo_working_copy(work_path, df_m, df_f, df_g)
        st.success(f"Saved working copy: {work_path} and ~/Downloads/'Psuedo Codes.xlsx'")

        st.download_button(
            "⬇️ Psuedo Codes.xlsx",
            data=out_bytes,
            file_name="Psuedo Codes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="pc_dl"
        )

# ---------------------- STEP 3: Map SPEAKER_XX -> Names -> Codes (final, append workbook) ----------------------
if st.session_state.pipeline_ready and st.session_state.pseudo_state["loaded"]:
    st.markdown("---")
    st.header("🎯 Map speakers to names (no codes shown) and export final")

    words: List[Dict[str, Any]] = st.session_state.words
    turns: List[Dict[str, Any]] = st.session_state.turns
    audio_name: str = st.session_state.audio_name

    # Collect unique speaker tags in ascending order
    spk_tags = sorted({w.get("speaker","SPEAKER_00") for w in words})
    spk_tags.sort(key=lambda s: int(s.split("_")[1]) if s.startswith("SPEAKER_") else 999)

    # DataFrames from pseudo workbook (Name, Code)
    df_m, df_f, df_g = st.session_state.pseudo_state["dfs"]
    names_by_cat = {
        "Mentors": sorted([n for n in df_m["Name"] if isinstance(n,str) and n.strip()]),
        "Founders": sorted([n for n in df_f["Name"] if isinstance(n,str) and n.strip()]),
        "Guests": sorted([n for n in df_g["Name"] if isinstance(n,str) and n.strip()]),
    }

    # name -> code (case-insensitive)
    name_to_code = {}
    for df in (df_m, df_f, df_g):
        for n, c in zip(df["Name"], df["Code"]):
            if isinstance(n, str) and n.strip():
                name_to_code[n.strip().lower()] = c

    mapping_path_str = st.text_input(
        "Path to Speaker Mapping Excel (append mode; updates/creates two sheets: Names & Codes)",
        value="",
        help="Example: /Users/arya/Downloads/Speaker Mapping.xlsx"
    )

    if "spk_map_state" not in st.session_state:
        st.session_state.spk_map_state = {}

    # Initialize defaults
    for spk in spk_tags:
        if f"cat_{spk}" not in st.session_state:
            st.session_state[f"cat_{spk}"] = "Mentors"
        if f"name_{spk}" not in st.session_state:
            opts0 = names_by_cat.get(st.session_state[f"cat_{spk}"], [])
            st.session_state[f"name_{spk}"] = (opts0[0] if opts0 else "")
        if spk not in st.session_state.spk_map_state:
            st.session_state.spk_map_state[spk] = {
                "cat": st.session_state[f"cat_{spk}"],
                "name": st.session_state[f"name_{spk}"],
            }

    def on_change_cat(spk_key: str):
        cat = st.session_state.get(f"cat_{spk_key}", "Mentors")
        opts = names_by_cat.get(cat, [])
        st.session_state[f"name_{spk_key}"] = (opts[0] if opts else "")
        st.session_state.spk_map_state[spk_key] = {
            "cat": cat,
            "name": st.session_state.get(f"name_{spk_key}", ""),
        }
        st.rerun()

    def on_change_name(spk_key: str):
        name = st.session_state.get(f"name_{spk_key}", "")
        cat = st.session_state.get(f"cat_{spk_key}", "Mentors")
        st.session_state.spk_map_state[spk_key] = {"cat": cat, "name": name}

    st.subheader("Assign categories and names")
    for spk in spk_tags:
        colA, colB = st.columns([1, 2])
        with colA:
            st.selectbox(
                f"{spk}: Category",
                ["Mentors", "Founders", "Guests"],
                key=f"cat_{spk}",
                on_change=on_change_cat,
                args=(spk,),
            )
        with colB:
            current_cat = st.session_state.get(f"cat_{spk}", "Mentors")
            name_opts = names_by_cat.get(current_cat, [])
            if not name_opts:
                name_opts = ["-- No names in this category --"]
            current_name = st.session_state.get(f"name_{spk}", "")
            if current_name not in name_opts:
                st.session_state[f"name_{spk}"] = name_opts[0]
            st.selectbox(
                f"{spk}: Name",
                name_opts,
                key=f"name_{spk}",
                on_change=on_change_name,
                args=(spk,),
            )

    st.markdown("")
    gen = st.button("Generate final files")

    if gen:
        # Build mapping SPEAKER_XX -> pseudo code
        spk_to_code: Dict[str, str] = {}
        spk_to_name: Dict[str, str] = {}
        errors = []
        for spk in spk_tags:
            nm = st.session_state.get(f"name_{spk}", "").strip()
            spk_to_name[spk] = nm if nm != "-- No names in this category --" else ""
            code = name_to_code.get((nm or "").lower(), "")
            if not nm or nm == "-- No names in this category --" or not code:
                errors.append(f"{spk} is not fully mapped. Please choose a name with an assigned code.")
            else:
                spk_to_code[spk] = code

        if errors:
            st.error("• " + "\n• ".join(errors))
        else:
            import copy
            words_final = copy.deepcopy(st.session_state.words)
            for w in words_final:
                sp = w.get("speaker","SPEAKER_00")
                w["speaker"] = spk_to_code.get(sp, sp)

            turns_final = copy.deepcopy(st.session_state.turns)
            for t in turns_final:
                sp = t.get("speaker","SPEAKER_00")
                t["speaker"] = spk_to_code.get(sp, sp)

            # Final files
            final_txt = turns_to_txt(turns_final)
            final_json_bytes = json.dumps(words_final, ensure_ascii=False, indent=2).encode("utf-8")

            st.download_button(
                "⬇️ Final transcript (txt)",
                data=final_txt.encode("utf-8"),
                file_name=f"{audio_name}_final.txt",
                mime="text/plain",
                key="final_txt_dl"
            )
            st.download_button(
                "⬇️ Final words (json)",
                data=final_json_bytes,
                file_name=f"{audio_name}_final_words.json",
                mime="application/json",
                key="final_json_dl"
            )

            # ZIP
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"{audio_name}_final.txt", final_txt)
                zf.writestr(f"{audio_name}_final_words.json", final_json_bytes)
            zip_data = zip_buf.getvalue()
            st.download_button(
                "⬇️ Download final folder (ZIP)",
                data=zip_data,
                file_name=f"{audio_name}_final.zip",
                mime="application/zip",
                key="final_zip_dl"
            )

            # Speaker Mapping Workbook (Names & Codes) for this audio — KEY = ID
            key_col = "ID"
            cols = [key_col] + spk_tags
            row_names = {key_col: audio_name}
            row_codes = {key_col: audio_name}
            for spk in spk_tags:
                row_names[spk] = spk_to_name.get(spk, "")
                row_codes[spk] = spk_to_code.get(spk, "")
            df_names = pd.DataFrame([row_names], columns=cols)
            df_codes = pd.DataFrame([row_codes], columns=cols)

            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                df_names.to_excel(writer, sheet_name="Names", index=False)
                df_codes.to_excel(writer, sheet_name="Codes", index=False)
            excel_bytes = excel_buf.getvalue()
            st.download_button(
                "⬇️ Speaker Mapping Workbook (Names & Codes)",
                data=excel_bytes,
                file_name=f"{audio_name}_speaker_mapping.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="spk_map_xlsx"
            )

            # Append/update persistent mapping workbook (ID-based)
            if mapping_path_str.strip():
                try:
                    append_mapping_to_excel(
                        Path(mapping_path_str.strip()),
                        df_names,
                        df_codes,
                        spk_tags,
                        key_col=key_col,
                    )
                    st.success(f"Updated mapping workbook: {mapping_path_str.strip()}")
                except Exception as e:
                    st.error(f"Failed to update mapping workbook: {e}")

            # SAVE_LOCAL option
            if st.sidebar.checkbox("Confirm SAVE_LOCAL for final files", value=False, key="save_local_final"):
                final_dir = Path.home() / "Desktop" / f"{audio_name}_final"
                final_dir.mkdir(parents=True, exist_ok=True)
                (final_dir / f"{audio_name}_final.txt").write_text(final_txt, encoding="utf-8")
                (final_dir / f"{audio_name}_final_words.json").write_bytes(final_json_bytes)
                (final_dir / f"{audio_name}_final.zip").write_bytes(zip_data)
                (final_dir / f"{audio_name}_speaker_mapping.xlsx").write_bytes(excel_bytes)
                st.success(f"Final files saved to: {final_dir}")

# Reset control
if st.session_state.pipeline_ready and st.button("🔄 Reset and start a new file"):
    for k in ("pipeline_ready","words","turns","audio_name","out_dir","pseudo_state","spk_map_state"):
        if k in st.session_state: del st.session_state[k]
    st.rerun()
