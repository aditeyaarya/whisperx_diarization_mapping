import streamlit as st

BOARDROOM_CSS = """
<style>
:root{
  --sidebar:#1C352D; --bg:#F9F6EE; --text:#000000; --btn:#8B7355; --btnH:#6E5B3F;
}
html, body, [data-testid="stAppViewContainer"]{ background:var(--bg)!important;color:var(--text)!important;font-family:Georgia,"Times New Roman",serif!important;}
h1,h2,h3,h4,h5,h6{ font-family:Georgia,"Times New Roman",serif!important;color:var(--text)!important;letter-spacing:.2px; }
header[data-testid="stHeader"]{ background:var(--sidebar)!important;color:#fff!important;border-bottom:1px solid rgba(0,0,0,.18);}
[data-testid="stSidebar"]{ background:var(--sidebar)!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] h4,[data-testid="stSidebar"] h5,[data-testid="stSidebar"] h6,[data-testid="stSidebar"] label,[data-testid="stSidebar"] .stMarkdown{ color:#fff!important;font-weight:700!important;font-family:Georgia,"Times New Roman",serif!important;}
[data-testid="stSidebar"] .stTextInput input,[data-testid="stSidebar"] .stNumberInput input,[data-testid="stSidebar"] .stDateInput input,[data-testid="stSidebar"] .stPassword input,textarea,[data-testid="stSidebar"] .stTextArea textarea,[data-testid="stSidebar"] [data-baseweb="select"]>div{ background:#fff!important;color:var(--text)!important;border:1px solid rgba(0,0,0,.28)!important;border-radius:8px!important;min-height:40px!important;}
[data-testid="stSidebar"] input::placeholder,[data-testid="stSidebar"] textarea::placeholder{ color:rgba(0,0,0,.55)!important;}
ul[role="listbox"],div[role="listbox"]{ background:#fff!important;color:var(--text)!important;border:1px solid rgba(0,0,0,.2)!important;}
[data-testid="stSidebar"] [data-baseweb="select"] svg{ fill:var(--text)!important;color:var(--text)!important;}
.stTextInput input,.stNumberInput input,.stDateInput input,.stPassword input,textarea,.stTextArea textarea,[data-baseweb="select"]>div{ background:#fff!important;color:var(--text)!important;border:1px solid rgba(0,0,0,.22)!important;border-radius:8px!important;min-height:40px!important;}
.stTextInput input::placeholder,.stNumberInput input::placeholder,.stDateInput input::placeholder,.stPassword input::placeholder,textarea::placeholder{ color:rgba(0,0,0,.55)!important;}
[data-testid="stFileUploaderDropzone"]{ background:#fff!important;border:1.5px dashed rgba(0,0,0,.35)!important;border-radius:8px!important;color:var(--text)!important;padding:.4rem .6rem!important;min-height:48px!important;}
[data-testid="stFileUploaderDropzone"] *{ color:var(--text)!important;font-weight:500!important;font-size:.85rem!important;}
[data-testid="stFileUploaderDropzone"] button{ background:var(--btn)!important;color:#fff!important;font-weight:600!important;border-radius:6px!important;padding:.3rem .8rem!important;border:none!important;font-size:.85rem!important;}
[data-testid="stFileUploaderDropzone"] button:hover{ background:var(--btnH)!important;color:#fff!important;}
.stButton>button,.stDownloadButton>button{ background:var(--btn)!important;color:#fff!important;border-radius:8px!important;font-weight:700!important;padding:.5rem 1rem!important;}
.stButton>button:hover,.stDownloadButton>button:hover{ background:var(--btnH)!important;color:#fff!important;}
div[data-testid="stAlert"]{ border-radius:8px!important;font-weight:700!important;padding:.8rem 1rem!important;font-family:Georgia,"Times New Roman",serif!important;color:#000!important;}
div[data-testid="stAlert"].st-error{background:#FADBD8!important;}div[data-testid="stAlert"].st-warning{background:#FDEBD0!important;}div[data-testid="stAlert"].st-success{background:#D5F5E3!important;}
div[data-testid="stAlert"] p,div[data-testid="stAlert"] span,div[data-testid="stAlert"] div[role="alert"]{ color:#000!important;font-weight:600!important;}
[data-testid="stTable"] table,.stDataFrame table{ background:#fff!important;color:#000!important;border:1px solid rgba(0,0,0,.12);font-family:Georgia,"Times New Roman",serif!important;}
[data-testid="stTable"] th,.stDataFrame th{ background:var(--sidebar)!important;color:#fff!important;}
[data-testid="stProgressBar"] div div{ background:var(--btn)!important;}
</style>
"""

def inject_theme(css: str = BOARDROOM_CSS):
    st.markdown(css, unsafe_allow_html=True)
