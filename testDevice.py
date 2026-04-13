"""Find Sound device"""
import pyaudiowpatch as pyaudio

p = pyaudio.PyAudio()

print("\nAll devices:")
for i in range(p.get_device_count()):
    device = p.get_device_info_by_index(i)
    print(f"{i}: {device['name']} | loopback: {device['isLoopbackDevice']} | inputs: {device['maxInputChannels']}")

p.terminate()