"""Find Sample rate"""
import pyaudiowpatch as pyaudio

p = pyaudio.PyAudio()
device = p.get_device_info_by_index(27)
print(device)
p.terminate()