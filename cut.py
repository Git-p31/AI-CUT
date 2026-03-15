import streamlit as st
import os
import yt_dlp
import shutil
import subprocess
import time
from scenedetect import detect, ContentDetector, split_video_ffmpeg

# --- 1. CONFIG & CLONE 2SHORT.AI STYLE ---
st.set_page_config(page_title="2Short AI Clone", page_icon="🎬", layout="wide")

# Кастомный CSS для создания премиального темного интерфейса
st.markdown("""
    <style>
    /* Глобальный темный фон */
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Скрытие стандартных элементов */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stDeployButton {display:none;}

    /* Стилизация карточек (Glassmorphism) */
    div[data-testid="stVerticalBlock"] > div:has(div.stSubheader) {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 30px;
        border-radius: 24px;
        backdrop-filter: blur(10px);
    }

    /* Кнопки как на 2short (Оранжевый градиент) */
    .stButton>button {
        background: linear-gradient(90deg, #ff5c35 0%, #ff8035 100%) !important;
        color: white !important;
        border-radius: 50px !important;
        border: none !important;
        padding: 12px 24px !important;
        font-weight: bold !important;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
        box-shadow: 0 4px 15px rgba(255, 92, 53, 0.3);
    }
    
    /* Инпуты */
    .stTextInput>div>div>input {
        background-color: #111 !important;
        color: white !important;
        border: 1px solid #333 !important;
        border-radius: 12px !important;
    }

    /* Тарифные карточки в сайдбаре */
    .plan-box {
        background: #111;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #222;
        margin-bottom: 10px;
    }
    .plan-active { border-color: #ff5c35; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LOGIC ---
if 'plan' not in st.session_state:
    st.session_state.plan = "Free"

def fix_ffmpeg():
    try:
        path = subprocess.check_output(["where", "ffmpeg"]).decode("cp866").split('\r\n')[0]
        os.environ["PATH"] += os.pathsep + os.path.dirname(path)
    except: pass

fix_ffmpeg()

video_path = "temp_video.mp4"
output_dir = "output_scenes"

# --- 3. SIDEBAR (PLANS & SETTINGS) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/716/716429.png", width=50) # Логотип
    st.title("AI Video Pro")
    
    st.write("---")
    st.subheader("💎 Your Plan")
    
    plans = ["Free", "Starter", "Pro"]
    for p in plans:
        is_active = st.session_state.plan == p
        style = "plan-active" if is_active else ""
        if st.button(f"{p} {'(Active)' if is_active else ''}", key=f"p_{p}"):
            st.session_state.plan = p
            st.rerun()

    st.write("---")
    st.subheader("⚙️ AI Parameters")
    th = st.slider("Sensitivity", 10, 100, 30)
    min_s = st.number_input("Min Length (frames)", 10, 100, 20)
    
    if st.button("🗑 Reset Project"):
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(output_dir): shutil.rmtree(output_dir, ignore_errors=True)
        st.rerun()

# --- 4. MAIN CONTENT (Like 2short Explore) ---
st.markdown("<h1 style='text-align: center; font-size: 48px;'>Extract viral clips <span style='color: #ff5c35;'>instantly</span>.</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #888;'>AI-powered scene detection to help you grow faster.</p>", unsafe_allow_html=True)

# Центральная панель загрузки
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    st.subheader("🚀 Get Started")
    url = st.text_input("", placeholder="Paste YouTube link or upload file...")
    
    if url and st.button("Analyze Video"):
        with st.spinner("Processing magic..."):
            ydl_opts = {'format': 'best[ext=mp4]/best', 'outtmpl': video_path, 'overwrites': True}
            if st.session_state.plan == "Free":
                ydl_opts['download_ranges'] = lambda info_dict, ydl: [{'start_time': 0, 'end_time': 60}]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            st.rerun()

    if os.path.exists(video_path):
        st.divider()
        st.video(video_path)
        if st.button("✨ GENERATE CLIPS"):
            if not os.path.exists(output_dir): os.makedirs(output_dir)
            with st.spinner("AI is thinking..."):
                detector = ContentDetector(threshold=th, min_scene_len=min_s)
                scene_list = detect(video_path, detector)
                split_video_ffmpeg(video_path, scene_list, output_dir=output_dir, arg_override='-y')
                st.success(f"Generated {len(scene_list)} viral clips!")

# --- 5. RESULTS GRID ---
if os.path.exists(output_dir):
    files = [f for f in os.listdir(output_dir) if f.endswith(".mp4")]
    if files:
        st.write("---")
        st.subheader("📦 Generated Assets")
        grid = st.columns(4)
        for i, f in enumerate(files):
            with grid[i%4]:
                st.markdown(f"""
                    <div style='background: #111; padding: 15px; border-radius: 15px; border: 1px solid #333; margin-bottom: 10px; text-align:center;'>
                        <p style='color: #888; font-size: 12px;'>Scene {i+1}</p>
                    </div>
                """, unsafe_allow_html=True)
                with open(os.path.join(output_dir, f), "rb") as file:
                    st.download_button(f"Download", file, file_name=f, key=f"dl_{i}")