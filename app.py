import streamlit as st
import librosa
import base64
import os
import tempfile
from moviepy.editor import VideoFileClip

st.set_page_config(page_title="舞蹈卡点神器", layout="wide")
st.title("📱 随身舞蹈解析系统 (8拍网格版)")

# ==========================================
# a. 核心基建：人机协同锚点校准
# ==========================================
st.markdown("### 🎛️ 乐理校准器")
st.markdown("机器算节拍，人类找起点。听出第一个「1拍」所在的秒数，输入下方：")
# 让用户主导定调，解决机器无法识别乐句起点的问题
anchor_time = st.number_input("输入第一拍秒数 (例如: 2.5)", min_value=0.0, value=0.0, step=0.1)

uploaded_file = st.file_uploader("上传视频 (MP4)", type=["mp4"])

if uploaded_file is not None:
    with st.spinner("⏳ 正在解析 BPM 与底层音频数据..."):
        # ==========================================
        # b. 核心算法：后台数据计算
        # ==========================================
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "temp_video.mp4")
            audio_path = os.path.join(temp_dir, "temp_audio.wav")
            
            with open(video_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
                
            clip = VideoFileClip(video_path)
            clip.audio.write_audiofile(audio_path, logger=None)
            
            y, sr = librosa.load(audio_path)
            _, y_percussive = librosa.effects.hpss(y)
            tempo, drum_frames = librosa.beat.beat_track(y=y_percussive, sr=sr)
            drum_times = [round(float(t), 3) for t in librosa.frames_to_time(drum_frames, sr=sr)]
            
            onset_env_bass = librosa.onset.onset_strength(y=y, sr=sr, fmax=250, n_mels=16)
            bass_frames = librosa.onset.onset_detect(onset_envelope=onset_env_bass, sr=sr)
            bass_times = [round(float(t), 3) for t in librosa.frames_to_time(bass_frames, sr=sr)]
            
            bpm_value = float(tempo[0])
            
            with open(video_path, "rb") as f:
                video_b64 = base64.b64encode(f.read()).decode('ascii')

        st.success(f"✅ 解析完毕！机器测算匀速 BPM: {bpm_value:.1f}")
        
        # ==========================================
        # c. 前端交互：绘制带有绝对数字标尺的 8 拍网格
        # ==========================================
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
                #waveform {{ width: 100vw; margin-left: -5px; background: #1e1e1e; padding: 10px 0; overflow-x: hidden; }}
                .btn {{ background: #ff5722; color: white; border: none; padding: 15px 0; width: 100%; font-size: 18px; font-weight: bold; border-radius: 8px; cursor: pointer; margin-top: 10px; }}
                .btn:active {{ background: #e64a19; }}
                /* 新增网格字样 UI */
                .region-beat {{ color: rgba(255,255,255,0.7); font-size: 12px; padding: 2px; }}
                .region-one {{ color: #ffffff; font-size: 16px; font-weight: bold; padding: 2px 6px; background: rgba(255,87,34,0.8); border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
            </style>
        </head>
        <body>
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
                // 缩放视口：确保手机屏幕能完整显示 1 到 1.5 个八拍，不再眼花缭乱
                const pxPerSec = window.innerWidth / (secondsFor8Beats * 1.5); 

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
                
                // 接收用户定义的起始点和节拍时长
                const anchor = {anchor_time};
                const beatInterval = 60 / bpm;

                wavesurfer.on('decode', () => {{
                    // 图层1：把 Drum 和 Bass 弱化，只作为背景音效参考色块
                    drumTimes.forEach(time => {{
                        wsRegions.addRegion({{
                            start: time, end: time + 0.05, 
                            color: 'rgba(255, 215, 0, 0.2)', drag: false, resize: false
                        }});
                    }});
                    bassTimes.forEach(time => {{
                        wsRegions.addRegion({{
                            start: time, end: time + 0.15, 
                            color: 'rgba(0, 191, 255, 0.15)', drag: false, resize: false
                        }});
                    }});

                    // 图层2：硬核覆盖！根据用户锚点，推演并画出完美的 8 拍网格
                    if(anchor >= 0) {{
                        for (let i = 0; i < 30; i++) {{ // 假设最多往后铺 30 个 8拍
                            for (let beat = 1; beat <= 8; beat++) {{
                                let time = anchor + (i * 8 + (beat - 1)) * beatInterval;
                                
                                if (time >= 0) {{
                                    const isOne = (beat === 1);
                                    wsRegions.addRegion({{
                                        start: time,
                                        end: time + 0.02,
                                        // 如果是第一拍，显示醒目的红底白字，其它显示普通数字
                                        color: isOne ? 'transparent' : 'rgba(255, 255, 255, 0.3)',
                                        content: isOne ? '<div class="region-one">🚩 1</div>' : '<div class="region-beat">' + beat + '</div>',
                                        drag: false, resize: false
                                    }});
                                }}
                            }}
                        }}
                    }}
                }});

                playBtn.addEventListener('click', () => {{
                    wavesurfer.playPause();
                }});
            </script>
        </body>
        </html>
        """
        st.components.v1.html(html_code, height=650, scrolling=False)
