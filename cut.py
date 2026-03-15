import streamlit as st
import yt_dlp
import os
import shutil
import subprocess
import time
from faster_whisper import WhisperModel

# Настройки путей
VIDEO = "input_video.mp4"
AUDIO = "temp_audio.wav"
CLIPS = "output_clips"

if "logs" not in st.session_state:
    st.session_state.logs = "=== Система готова ===\n"

def add_log(message):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.logs += f"[{timestamp}] {message}\n"

@st.cache_resource
def load_smart_model():
    return WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")

st.set_page_config(page_title="One-Button AI Clips", page_icon="🎬", layout="wide")

# --- UI КОНСОЛЬ ---
with st.expander("🖥️ СТАТУС ОБРАБОТКИ", expanded=True):
    console_placeholder = st.empty()
    def update_console():
        console_placeholder.code(st.session_state.logs, language="bash")
    update_console()

# --- ЕДИНАЯ ФУНКЦИЯ ОБРАБОТКИ ---

def start_full_process(url, clip_len, max_count, user_prompt):
    try:
        # 1. СКАЧИВАНИЕ
        add_log(f"Начинаю загрузку: {url}")
        update_console()
        if os.path.exists(VIDEO): os.remove(VIDEO)
        ydl_opts = {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]', 'outtmpl': VIDEO, 'merge_output_format': 'mp4'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 2. АУДИО И ИИ
        add_log("Загрузка модели и анализ звука...")
        update_console()
        model = load_smart_model()
        if os.path.exists(AUDIO): os.remove(AUDIO)
        subprocess.run(["ffmpeg", "-i", VIDEO, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", AUDIO, "-y"], check=True, capture_output=True)
        
        segments, _ = model.transcribe(AUDIO, beam_size=5, initial_prompt=user_prompt, vad_filter=True)
        
        # 3. ПОИСК МОМЕНТОВ
        viral_triggers = ["wait", "what", "crazy", "insane", "omg", "look", "wow"]
        clips_meta = []
        for s in segments:
            if any(w in s.text.lower() for w in viral_triggers):
                clips_meta.append({"start": max(0, s.start - 1.5), "end": s.start + clip_len, "text": s.text.strip()})
        
        clips_meta = clips_meta[:max_count]
        
        # 4. НАРЕЗКА
        if os.path.exists(CLIPS): shutil.rmtree(CLIPS)
        os.makedirs(CLIPS)

        for i, meta in enumerate(clips_meta):
            add_log(f"Создаю клип {i+1}...")
            update_console()
            out_path = f"{CLIPS}/clip_{i}.mp4"
            clean_text = meta['text'].replace("'", "").upper()
            cmd = [
                "ffmpeg", "-ss", str(meta['start']), "-t", str(meta['end'] - meta['start']), "-i", VIDEO,
                "-vf", f"crop=ih*9/16:ih,drawtext=text='{clean_text}':fontcolor=yellow:fontsize=40:borderw=2:x=(w-text_w)/2:y=h-150",
                "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", out_path, "-y"
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
        add_log("✨ ВСЕ ГОТОВО!")
        update_console()
        
    except Exception as e:
        add_log(f"❌ ОШИБКА: {str(e)}")
        update_console()

# --- ИНТЕРФЕЙС ---

with st.sidebar:
    st.header("⚙️ Настройки")
    clip_len = st.slider("Длина клипа", 5, 30, 15)
    max_count = st.slider("Макс. клипов", 1, 10, 3)
    u_prompt = st.text_input("О чем видео?", "блог, юмор, подкаст")
    
    st.divider()
    if st.button("🗑️ ОЧИСТИТЬ ВСЕ РЕЗУЛЬТАТЫ", use_container_width=True):
        if os.path.exists(CLIPS): shutil.rmtree(CLIPS)
        if os.path.exists(VIDEO): os.remove(VIDEO)
        if os.path.exists(AUDIO): os.remove(AUDIO)
        st.session_state.logs = "=== Система очищена ===\n"
        st.rerun()

st.title("🎬 AI Viral Generator")
url = st.text_input("Вставьте ссылку на YouTube", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🚀 СОЗДАТЬ КЛИПЫ", use_container_width=True, type="primary"):
    if url:
        start_full_process(url, clip_len, max_count, u_prompt)
    else:
        st.error("Сначала вставьте ссылку!")

# ВЫВОД КЛИПОВ
if os.path.exists(CLIPS) and os.listdir(CLIPS):
    st.divider()
    st.subheader("📺 Готовые клипы")
    files = sorted([f for f in os.listdir(CLIPS) if f.endswith(".mp4")])
    cols = st.columns(2)
    for idx, f in enumerate(files):
        with cols[idx % 2]:
            path = os.path.join(CLIPS, f)
            st.video(path)
            with open(path, "rb") as bfile:
                st.download_button(f"Скачать {f}", bfile, file_name=f, key=f"btn_{f}")