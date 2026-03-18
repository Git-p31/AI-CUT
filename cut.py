import streamlit as st
import os
import asyncio
import edge_tts
import yt_dlp
import shutil
from moviepy import VideoFileClip, AudioFileClip
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator

# --- НАСТРОЙКИ ГОЛОСОВ ---
VOICE_DATA = {
    "ru": {"Male": "ru-RU-DmitryNeural", "Female": "ru-RU-SvetlanaNeural"},
    "en": {"Male": "en-US-GuyNeural", "Female": "en-US-JennyNeural"},
    "de": {"Male": "de-DE-ConradNeural", "Female": "de-DE-KatjaNeural"},
    "fr": {"Male": "fr-FR-HenriNeural", "Female": "fr-FR-DeniseNeural"},
    "es": {"Male": "es-ES-AlvaroNeural", "Female": "es-ES-ElviraNeural"}
}

st.set_page_config(page_title="AI Video Editor", page_icon="🎬", layout="wide")
st.title("🎬 AI Video Dubbing: Транскрибация и Редактирование")

# Инициализация хранилища текста
if "translated_text" not in st.session_state:
    st.session_state.translated_text = ""

# --- UI ---
st.subheader("1. Загрузка видео")
col_load1, col_load2 = st.columns(2)
uploaded_file = col_load1.file_uploader("Загрузите файл", type=["mp4", "mov", "avi"])
url = col_load2.text_input("ИЛИ ссылка на YouTube")

st.divider()

st.subheader("2. Параметры")
c1, c2, c3 = st.columns(3)
target_lang = c1.selectbox("Язык перевода", list(VOICE_DATA.keys()))
gender = c2.radio("Пол голоса", ["Male", "Female"], horizontal=True)
speed = c3.slider("Скорость речи (%)", 80, 150, 100)

VIDEO_PATH = "input_video.mp4"
VOICEOVER_PATH = "translated_voice.mp3"
RESULT_PATH = "translated_video.mp4"

# --- ЭТАП 1: ТРАНСКРИБАЦИЯ ---
if st.button("🔍 ЭТАП 1: ПОЛУЧИТЬ ТЕКСТ"):
    if uploaded_file or url:
        with st.spinner("Загрузка и распознавание..."):
            # Загрузка
            if uploaded_file:
                with open(VIDEO_PATH, "wb") as f: f.write(uploaded_file.getbuffer())
            else:
                ydl_opts = {'format': 'best[ext=mp4]', 'outtmpl': VIDEO_PATH, 'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])

            # Распознавание
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(VIDEO_PATH)
            full_text = " ".join([seg.text for seg in segments])
            
            # Перевод
            translator = GoogleTranslator(source='auto', target=target_lang)
            st.session_state.translated_text = translator.translate(full_text)
            st.success("Текст готов для редактирования!")
    else:
        st.warning("Сначала загрузите видео!")

# --- ПОЛЕ РЕДАКТИРОВАНИЯ ---
st.session_state.translated_text = st.text_area(
    "Отредактируйте текст перевода здесь перед озвучкой:", 
    value=st.session_state.translated_text, 
    height=250
)

# --- ЭТАП 2: ГЕНЕРАЦИЯ ---
if st.button("🚀 ЭТАП 2: СКЛЕИТЬ ВИДЕО С ЭТИМ ТЕКСТОМ"):
    if not st.session_state.translated_text:
        st.error("Нет текста для озвучки! Сначала выполните Этап 1 или введите текст вручную.")
    elif not os.path.exists(VIDEO_PATH):
        st.error("Файл видео не найден. Загрузите его снова.")
    else:
        try:
            # 1. Озвучка
            with st.spinner("Создание нейронного голоса..."):
                rate = f"{speed-100:+d}%"
                communicate = edge_tts.Communicate(st.session_state.translated_text, VOICE_DATA[target_lang][gender], rate=rate)
                asyncio.run(communicate.save(VOICEOVER_PATH))

            # 2. Монтаж
            with st.spinner("Сборка финального видео..."):
                video = VideoFileClip(VIDEO_PATH)
                new_audio = AudioFileClip(VOICEOVER_PATH)
                
                final_video = video.with_audio(new_audio)
                final_video.write_videofile(RESULT_PATH, codec="libx264", audio_codec="aac", fps=24)
                
                st.success("🔥 ГОТОВО!")
                st.video(RESULT_PATH)
                
                with open(RESULT_PATH, "rb") as f:
                    st.download_button("📥 Скачать результат", f, "dubbed_video.mp4")
                
                video.close()
                new_audio.close()
        except Exception as e:
            st.error(f"Ошибка: {e}")