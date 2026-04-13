import vosk
import pyaudiowpatch as pyaudio
import queue
import json
import sys
import threading
import signal
import numpy as np
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont


MODEL_PATH = "vosks models/vosk-model-en-us-0.22-lgraph"
SAMPLE_RATE = 16000
DEVICE_SAMPLE_RATE = 44100
CHUNK = 4096
LOOPBACK_DEVICE_INDEX = 27

q = queue.Queue()

class Communicator(QObject):
    text_updated = pyqtSignal(str)

class Overlay(QWidget):
    def __init__(self, comm):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 800, 1000, 80)

        self.label = QLabel("Listening...", self)
        self.label.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.label.setStyleSheet("""
            color: white;
            background-color: rgba(0, 0, 0, 160);
            border-radius: 10px;
            padding: 8px 16px;
        """)
        self.label.setWordWrap(True)
        self.label.setGeometry(0, 0, 1000, 80)

        comm.text_updated.connect(self.update_text)

    def update_text(self, text):
        self.label.setText(text)

def resample(data, from_rate, to_rate):
    audio = np.frombuffer(data, dtype=np.int16)
    audio = audio.reshape(-1, 2).mean(axis=1).astype(np.int16)
    num_samples = int(len(audio) * to_rate / from_rate)
    resampled = np.interp(
        np.linspace(0, len(audio), num_samples),
        np.arange(len(audio)),
        audio
    ).astype(np.int16)
    return resampled.tobytes()

def transcription_thread(comm):
    model = vosk.Model(MODEL_PATH)
    recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    while True:
        data = q.get()
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            if result['text']:
                comm.text_updated.emit(result['text'])
        else:
            partial = json.loads(recognizer.PartialResult())
            if partial['partial']:
                comm.text_updated.emit(partial['partial'] + "...")

def audio_thread():
    p = pyaudio.PyAudio()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=2,
        rate=DEVICE_SAMPLE_RATE,
        input=True,
        input_device_index=LOOPBACK_DEVICE_INDEX,
        frames_per_buffer=CHUNK
    )

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        resampled = resample(data, DEVICE_SAMPLE_RATE, SAMPLE_RATE)
        q.put(resampled)

app = QApplication(sys.argv)
signal.signal(signal.SIGINT, signal.SIG_DFL)
comm = Communicator()
overlay = Overlay(comm)
overlay.show()

threading.Thread(target=transcription_thread, args=(comm,), daemon=True).start()
threading.Thread(target=audio_thread, daemon=True).start()

sys.exit(app.exec())