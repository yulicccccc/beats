import streamlit as st
import librosa
import base64
import os
import tempfile
from moviepy.editor import VideoFileClip

# ==========================================
# a. 核心基建：移动端 UI 布局与文件上传
# ==========================================
# 设置页面为宽屏模式，适配手机边界
st.set_page_config(page_title="舞蹈卡点神器", layout="wide")
st.title("📱 随身舞蹈解析系统")
st.markdown("上传手机相册里的舞蹈视频，自动提取 Drum & Bass 卡点。")

# 手机端友好的上传按钮
uploaded_file = st.file_uploader("点击这里上传视频 (MP4)", type=["mp4"])

if uploaded_file is not None:
    with st.spinner("⏳ 服务器正在飞速解析鼓点和贝斯，请稍候..."):
        # ==========================================
        # b. 核心算法：云端内存防弹处理
        # ==========================================
        # 创建安全的临时目录，防止云端多用户文件冲突
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "temp_video.mp4")
            audio_path = os.path.join(temp_dir, "temp_audio.wav")
            
            # 将用户上传的文件写入临时硬盘
            with open(video_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            # 从视频抽离音频
            clip = VideoFileClip(video_path)
            clip.audio.write_audiofile(audio_path, logger=None)
            
            # 读取并净化数据 (强制剥离 numpy float64 外衣)
            y, sr = librosa.load(audio_path)
            
            _, y_percussive = librosa.effects.hpss(y)
            tempo, drum_frames = librosa.beat.beat_track(y=y_percussive, sr=sr)
            drum_times = [round(float(t), 3) for t in librosa.frames_to_time(drum_frames, sr=sr)]
            
            onset_env_bass = librosa.onset.onset_strength(y=y, sr=sr, fmax=250, n_mels=16)
            bass_frames = librosa.onset.onset_detect(onset_envelope=onset_env_bass, sr=sr)
            bass_times = [round(float(t), 3) for t in librosa.frames_to_time(bass_frames, sr=sr)]
            
            bpm_value = float(tempo[0])
            
            # 将处理好的原视频转码，准备喂给前端
            with open(video_path, "rb") as f:
                video_b64 = base64.b64encode(f.read()).decode('ascii')

        # ==========================================
        # c. 前端交互：移动端 100vw 响应式渲染引擎
        # ==========================================
        st.success(f"✅ 解析完毕！BPM: {bpm_value:.1f}")
        
        # 针对手机端重写 CSS 样式，宽度拉满 100%
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <script src="https://unpkg.com/wavesurfer.js@7"></script>
            <script src="https://unpkg.com/wavesurfer.js@7/dist/plugins/regions.min.js"></script>
            <style>
                body {{ background-color: #121212; color: white; padding: 5px; margin: 0; font-family: sans-serif; }}
                #video-container {{ width: 100%; margin-bottom: 10px; }}
                video {{ width: 100%; border-radius: 8px; }}
                /* 波形图容器占满手机屏幕宽度 */
                #waveform {{ width: 100vw; margin-left: -5px; background: #1e1e1e; padding: 10px 0; overflow-x: hidden; }}
                .btn {{ background: #ff5722; color: white; border: none; padding: 15px 0; width: 100%; font-size: 18px; font-weight: bold; border-radius: 8px; cursor: pointer; margin-top: 10px; }}
                .btn:active {{ background: #e64a19; }}
                .legend {{ display: flex; justify-content: center; gap: 15px; margin: 10px 0; font-size: 12px; }}
                .legend-item {{ display: flex; align-items: center; gap: 5px; }}
                .color-box {{ width: 12px; height: 12px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="legend">
                <div class="legend-item"><div class="color-box" style="background: rgba(255, 215, 0, 0.7);"></div>🥁 Drum</div>
                <div class="legend-item"><div class="color-box" style="background: rgba(0, 191, 255, 0.5);"></div>🎸 Bass</div>
            </div>
            
            <div id="video-container">
                <video id="dance-video" src="data:video/mp4;base64,{video_b64}" playsinline></video>
            </div>
            
            <div id="waveform"></div>
            <button class="btn" id="play-btn">▶ 播放 / 暂停</button>

            <script>
                const videoEl = document.getElementById('dance-video');
                const playBtn = document.getElementById('play-btn');
                const waveformEl = document.getElementById('waveform');

                const bpm = {bpm_value}; 
                const secondsFor8Beats = (60 / bpm) * 8; 
                // 动态获取手机屏幕宽度
                const pxPerSec = window.innerWidth / secondsFor8Beats; 

                const wavesurfer = WaveSurfer.create({{
                    container: '#waveform',
                    waveColor: '#4a90e2',
                    progressColor: '#ff5722',
                    cursorColor: '#fff',
                    barWidth: 2,
                    media: videoEl,
                    minPxPerSec: pxPerSec, 
                    autoScroll: true       
                }});

                const wsRegions = wavesurfer.registerPlugin(WaveSurfer.Regions.create());
                
                const drumTimes = {drum_times};
                const bassTimes = {bass_times};

                wavesurfer.on('decode', () => {{
                    drumTimes.forEach(time => {{
                        wsRegions.addRegion({{
                            start: time, end: time + 0.05, 
                            color: 'rgba(255, 215, 0, 0.7)', drag: false, resize: false
                        }});
                    }});
                    
                    bassTimes.forEach(time => {{
                        wsRegions.addRegion({{
                            start: time, end: time + 0.15, 
                            color: 'rgba(0, 191, 255, 0.5)', drag: false, resize: false
                        }});
                    }});
                }});

                playBtn.addEventListener('click', () => {{
                    wavesurfer.playPause();
                }});
            </script>
        </body>
        </html>
        """
        # 在 Streamlit 中安全渲染前端代码
        st.components.v1.html(html_code, height=600, scrolling=False)
