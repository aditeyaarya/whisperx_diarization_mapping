# 🏛️ WhisperX + Word-Level Diarization (STRICT) + Pseudo Codes + Speaker Mapping

A Streamlit-based transcription and speaker mapping tool built on **WhisperX** and **Pyannote**, designed for **structured, privacy-safe diarization** with **deterministic pseudo codes** and robust Excel-based mapping.

---

## 🚀 Overview

This app performs:
- **WhisperX transcription** with word-level alignment  
- **Pyannote diarization** (STRICT mode — requires ≥ 2 unique speakers)  
- **Turn segmentation** from aligned words  
- **Speaker mapping** via Excel-based pseudo-code workbooks  
- **Safe Excel append/update** by ID for speaker mapping archives  

The workflow is split into 3 stages:
1. **Transcription + Alignment + Diarization**
2. **Pseudo-Code Workbook Management**
3. **Speaker Mapping & Final Export**

---

## ✨ Key Features

| Category | Description |
|-----------|--------------|
| 🎙️ **ASR + Diarization** | Transcribes using WhisperX and diarizes speakers via Pyannote |
| 🧩 **STRICT Mode** | Aborts automatically if < 2 speakers are detected |
| 🕒 **Word-Level Alignment** | Each word is timestamped and grouped into coherent turns |
| 🔐 **Pseudo Codes** | Deterministically generated mentor/founder/guest codes |
| 🧾 **Excel Integration** | Append or update a persistent Speaker Mapping Excel workbook by `ID` |
| 💾 **Optional Local Save** | Automatically saves files to `~/Desktop/<audio>_transcription/` and `<audio>_final/` |
| 🎨 **Wood & Cream Theme** | Elegant Streamlit theme for readability and professionalism |

---

## 🧰 Tech Stack

- **Language:** Python 3.10–3.12  
- **Framework:** Streamlit  
- **ASR & Diarization:** WhisperX + Pyannote  
- **Data Handling:** pandas, openpyxl, tqdm  
- **ML Backend:** PyTorch  

---

## 📦 Installation

### 1️⃣ Clone the repository
```bash
git clone https://github.com/<aditeyaarya>/whisperx-diar-mapper.git
cd whisperx-diarization-mapping
