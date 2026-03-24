import vosk
import sounddevice as sd
import queue
import json
import sys
import threading
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont

MODEL_PATH = "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16000

q = queue.Queue()

def callback(indata, frames, time, status):
    q.put(bytes(indata))

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

app = QApplication(sys.argv)
comm = Communicator()
overlay = Overlay(comm)
overlay.show()

thread = threading.Thread(target=transcription_thread, args=(comm,), daemon=True)
thread.start()

with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=1600, dtype='int16',
                       channels=1, callback=callback):
    sys.exit(app.exec())