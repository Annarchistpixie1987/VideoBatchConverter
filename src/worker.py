# src/worker.py
import os, sys, subprocess, logging
from pathlib import Path
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

def get_ffmpeg_path(tool='ffmpeg'):
    if getattr(sys, 'frozen', False): base_path = Path(sys.executable).parent
    else: base_path = Path(__file__).parent.parent
    ffmpeg_dir = base_path / 'assets' / 'ffmpeg'; tool_path = ffmpeg_dir / f'{tool}.exe'
    return str(tool_path) if tool_path.exists() else None

def get_video_duration(file_path):
    ffprobe_path = get_ffmpeg_path('ffprobe')
    if not ffprobe_path: return 0.0
    command = [ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)]
    startupinfo = None
    if os.name == 'nt': startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try: result = subprocess.run(command, capture_output=True, text=True, check=True, startupinfo=startupinfo); return float(result.stdout.strip())
    except (ValueError, subprocess.CalledProcessError) as e: logging.warning(f"'{file_path}'의 길이를 가져오는 데 실패했습니다: {e}"); return 0.0

def get_video_codec(file_path):
    ffprobe_path = get_ffmpeg_path('ffprobe');
    if not ffprobe_path: return None
    command = [ffprobe_path, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)]
    startupinfo = None
    if os.name == 'nt': startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    try: result = subprocess.run(command, capture_output=True, text=True, check=True, startupinfo=startupinfo); return result.stdout.strip()
    except subprocess.CalledProcessError as e: logging.warning(f"'{file_path}' 코덱 확인 실패: {e.stderr}"); return None
    except FileNotFoundError: logging.error("ffprobe를 찾을 수 없습니다."); return None

class WorkerSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(object, bool) # task 객체를 전달하기 위해 object 타입으로 변경

class FileConversionTask(QRunnable):
    def __init__(self, input_file, settings, signals):
        super().__init__()
        self.input_file = Path(input_file); self.settings = settings; self.signals = signals
        self.process = None # FFmpeg 프로세스 객체를 저장할 변수

    def run(self):
        try:
            ffmpeg_path = get_ffmpeg_path('ffmpeg')
            if not ffmpeg_path: self.signals.log.emit(f"오류: {self.input_file.name} - ffmpeg.exe를 찾을 수 없습니다."); self.signals.finished.emit(self, False); return
            
            suffix = self.settings['suffix']; output_file = self.input_file.with_stem(f"{self.input_file.stem}{suffix}")
            if output_file.exists(): self.signals.log.emit(f"결과: '{output_file.name}' 파일이 이미 존재하여 건너뜁니다."); self.signals.finished.emit(self, True); return
            
            duration = get_video_duration(self.input_file)
            if duration <= 0: self.signals.log.emit(f"경고: '{self.input_file.name}'의 길이를 알 수 없어 진행률 표시가 비활성화됩니다.")
            
            ffmpeg_cmd = self.build_ffmpeg_command(ffmpeg_path, self.input_file, output_file)
            logging.info(f"실행할 FFmpeg 명령어: {' '.join(ffmpeg_cmd)}")
            
            startupinfo = None
            if os.name == 'nt': startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', startupinfo=startupinfo)

            for line in iter(self.process.stdout.readline, ''):
                if 'out_time_ms' in line and duration > 0:
                    current_time_ms = int(line.strip().split('=')[1]); percentage = (current_time_ms / (duration * 1_000_000)) * 100
                    self.signals.progress.emit(str(self.input_file), int(percentage))
            
            self.process.wait()

            if self.process.returncode == 0:
                self.signals.log.emit(f"완료: '{output_file.name}' 변환 성공."); self.signals.finished.emit(self, True)
            # returncode가 음수이면 terminate()로 종료된 경우일 수 있으므로 별도 로그 불필요
            elif self.process.returncode > 0:
                self.signals.log.emit(f"오류: '{self.input_file.name}' 변환 실패 (오류 코드: {self.process.returncode})."); self.signals.finished.emit(self, False)
            else: # 중지된 경우
                self.signals.finished.emit(self, False)

        except Exception as e:
            logging.exception(f"'{self.input_file.name}' 처리 중 예외 발생"); self.signals.log.emit(f"치명적 오류: '{self.input_file.name}' - {e}"); self.signals.finished.emit(self, False)

    # --- 프로세스 종료를 위한 메소드 추가 ---
    def stop(self):
        if self.process and self.process.poll() is None:
            logging.warning(f"FFmpeg 프로세스 강제 종료 시도: {self.input_file.name}")
            self.process.terminate()

    def build_ffmpeg_command(self, ffmpeg_path, input_file, output_file):
        s = self.settings; ffmpeg_cmd = [ffmpeg_path, '-y', '-i', str(input_file)]; ffmpeg_cmd.extend(['-progress', 'pipe:1', '-nostats']); is_gpu = "GPU" in s['codec']; codec_map = {'H.265 (HEVC) - CPU': 'libx265', 'H.265 (HEVC) - GPU': 'hevc_nvenc', 'AV1 - CPU': 'libaom-av1', 'AV1 - GPU': 'av1_nvenc', 'VP9 - CPU': 'libvpx-vp9', 'AVC (H.264) - CPU': 'libx264', 'AVC (H.264) - GPU': 'h264_nvenc'}; encoder = codec_map[s['codec']]; ffmpeg_cmd.extend(['-c:v', encoder])
        if s['resolution'] != '원본 유지': res_map = {'1080p': '-1:1080', '720p': '-1:720', '480p': '-1:480'}; ffmpeg_cmd.extend(['-vf', f"scale={res_map[s['resolution']]}"])
        if is_gpu:
            preset_val = s['preset'].split(' ')[0]; ffmpeg_cmd.extend(['-preset', preset_val])
            if s['rate_control'] == 'CQP': ffmpeg_cmd.extend(['-cq', s['quality_value']])
            else: ffmpeg_cmd.extend(['-b:v', s['quality_value']])
        else:
            if s['rate_control'] == 'CRF': ffmpeg_cmd.extend(['-crf', s['quality_value']])
            else: ffmpeg_cmd.extend(['-b:v', s['quality_value']])
        audio_option = s['audio_option']
        if "Passthrough" in audio_option: ffmpeg_cmd.extend(['-c:a', 'copy'])
        else: bitrate = audio_option.split(' ')[1].replace('kbps', 'k'); ffmpeg_cmd.extend(['-c:a', 'aac', '-b:a', bitrate])
        ffmpeg_cmd.append(str(output_file)); return ffmpeg_cmd