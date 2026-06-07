import numpy as np
from scipy.io import wavfile
import os

def generate_beep(filename, frequency, duration, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Sine wave
    tone = np.sin(frequency * t * 2 * np.pi)
    # Simple fade out to avoid click
    fade_duration = int(sample_rate * 0.05)
    fade_out = np.linspace(1, 0, fade_duration)
    tone[-fade_duration:] *= fade_out
    
    # 16-bit PCM
    audio = (tone * (2**15 - 1)).astype(np.int16)
    wavfile.write(filename, sample_rate, audio)
    print(f"Generated {filename}")

os.makedirs("assets", exist_ok=True)
generate_beep("assets/tick.wav", 880, 0.1) # High pitch short tick
generate_beep("assets/final.wav", 440, 0.3) # Lower pitch longer final
