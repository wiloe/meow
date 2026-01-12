import wave
import struct
import random
import math
import os

def generate_burst_wav(filename="burst.wav", duration=0.5, volume=0.7, decay=True, frequency=440.0, end_frequency=None):
    """
    Generates a sine wave tone and saves it to a WAV file.
    
    Args:
        filename (str): Output filename.
        duration (float): Length of the burst in seconds.
        volume (float): Peak volume (0.0 to 1.0).
        decay (bool): If True, applies a fade-out to sound like an impact/burst.
                      If False, creates a solid tone.
        frequency (float): Frequency of the sine wave in Hz.
        end_frequency (float): End frequency for the slide. If None, stays constant.
    """
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    
    print(f"Generating {filename}...")
    print(f"Duration: {duration}s | Decay: {decay}")
    
    if end_frequency is None:
        end_frequency = frequency

    try:
        # Open the WAV file for writing
        # Parameters: (nchannels, sampwidth, framerate, nframes, comptype, compname)
        # 1 channel (mono), 2 bytes (16-bit PCM), 44100 Hz
        with wave.open(filename, 'w') as wav_file:
            wav_file.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
            
            # Constant for linear chirp: k = (f_end - f_start) / duration
            k = (end_frequency - frequency) / duration if duration > 0 else 0
            
            for i in range(num_samples):
                # Generate sine wave with frequency slide
                t = i / sample_rate
                phase = 2 * math.pi * (frequency * t + (k / 2) * t * t)
                wave_sample = math.sin(phase)
                
                # Apply volume
                current_volume = volume
                
                # Apply decay envelope if requested (makes it sound like a 'hit' or 'pshhht')
                # We use a simple linear fade out here. 
                # For a sharper burst, you could use exponential decay: volume * (0.9999 ** i)
                if decay:
                    progress = i / num_samples
                    # Linear fade out: (1 - progress)
                    current_volume = volume * (1 - progress)
                
                # Scale to 16-bit integer range (-32767 to 32767)
                sample_value = int(wave_sample * current_volume * 32767.0)
                
                # Clamp values just in case
                sample_value = max(min(sample_value, 32767), -32767)
                
                # Write sample as binary data (little-endian signed short)
                wav_file.writeframes(struct.pack('<h', sample_value))
                
        print(f"Success! Saved to: {os.path.abspath(filename)}")
        
    except Exception as e:
        print(f"Error generating wav file: {e}")

def generate_noise_wav(filename="noise.wav", duration=0.5, volume=0.5, decay=True):
    """Generates white noise for explosions or fuses."""
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    print(f"Generating noise {filename}...")
    
    try:
        with wave.open(filename, 'w') as wav_file:
            wav_file.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
            for i in range(num_samples):
                noise = random.uniform(-1.0, 1.0)
                
                # Envelope
                env = volume
                if decay: # Exponential decay for pop
                    env *= math.exp(-15.0 * (i / num_samples))
                else: # Constant with slight fade in/out for fuse
                    if i < 2000: env *= (i / 2000)
                    elif i > num_samples - 2000: env *= ((num_samples - i) / 2000)
                
                sample = int(noise * env * 32767.0)
                wav_file.writeframes(struct.pack('<h', max(min(sample, 32767), -32767)))
        print(f"Success! Saved to: {os.path.abspath(filename)}")
    except Exception as e:
        print(f"Error generating noise wav: {e}")

def generate_techno_wav(filename="music.wav", duration=10.0, bpm=120):
    """Generates a simple techno beat loop."""
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    print(f"Generating music {filename}...")
    
    beat_interval = 60.0 / bpm
    samples_per_beat = int(sample_rate * beat_interval)
    
    try:
        with wave.open(filename, 'w') as wav_file:
            wav_file.setparams((1, 2, sample_rate, num_samples, 'NONE', 'not compressed'))
            
            # Generate track in memory first (for mixing)
            # This is a simplified approach, writing directly would be harder to mix
            # We'll just write sample by sample mixing on the fly
            
            for i in range(num_samples):
                t = i / sample_rate
                
                # Kick Drum (Every beat)
                local_t = t % beat_interval
                kick = 0.0
                if local_t < 0.2:
                    freq = 150.0 * (1.0 - (local_t / 0.2))
                    kick = math.sin(2 * math.pi * freq * local_t) * (1.0 - local_t/0.2)
                
                # Hi-hat (Every off-beat)
                hat = 0.0
                if (t % (beat_interval/2)) > (beat_interval/4) and (t % (beat_interval/2)) < (beat_interval/4) + 0.05:
                    hat = random.uniform(-0.5, 0.5)
                
                # Mix
                sample = int((kick * 0.8 + hat * 0.3) * 32767.0)
                wav_file.writeframes(struct.pack('<h', max(min(sample, 32767), -32767)))
        print(f"Success! Saved to: {os.path.abspath(filename)}")
    except Exception as e:
        print(f"Error generating music wav: {e}")

if __name__ == "__main__":
    # Generate the file in the same directory as the script
    output_path = os.path.join(os.path.dirname(__file__), "burst.wav")
    generate_burst_wav(output_path, duration=0.2, frequency=880.0, end_frequency=100.0)
    
    fuse_path = os.path.join(os.path.dirname(__file__), "fuse.wav")
    generate_noise_wav(fuse_path, duration=1.0, volume=0.3, decay=False)
    
    pop_path = os.path.join(os.path.dirname(__file__), "pop.wav")
    generate_noise_wav(pop_path, duration=0.2, volume=0.8, decay=True)
    
    music_path = os.path.join(os.path.dirname(__file__), "music.wav")
    generate_techno_wav(music_path, duration=10.0, bpm=130)