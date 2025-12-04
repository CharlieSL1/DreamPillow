import numpy as np
from typing import List, Tuple
import struct


def load_mp3(file_path: str) -> Tuple[np.ndarray, int]:
    try:
        from pydub import AudioSegment
    except ImportError:
        raise ImportError("pydub required: pip install pydub")
    
    audio = AudioSegment.from_mp3(file_path)
    samples = audio.get_array_of_samples()
    channels = audio.channels
    sample_rate = audio.frame_rate
    
    if channels == 1:
        return np.array(samples, dtype=np.float32) / 32768.0, sample_rate
    else:
        return np.array(samples, dtype=np.float32).reshape(-1, channels) / 32768.0, sample_rate


def resample(audio_data: np.ndarray, original_sr: int, target_sr: int) -> np.ndarray:
    if original_sr == target_sr:
        return audio_data
    
    from scipy import signal
    
    if len(audio_data.shape) == 1:
        num_samples = int(len(audio_data) * target_sr / original_sr)
        return signal.resample(audio_data, num_samples).astype(np.float32)
    else:
        num_samples = int(len(audio_data) * target_sr / original_sr)
        resampled = np.zeros((num_samples, audio_data.shape[1]), dtype=np.float32)
        for ch in range(audio_data.shape[1]):
            resampled[:, ch] = signal.resample(audio_data[:, ch], num_samples)
        return resampled


def stereo_to_4ch(left: np.ndarray, right: np.ndarray) -> List[np.ndarray]:
    return [
        left.astype(np.float32),
        right.astype(np.float32),
        (left * 0.7).astype(np.float32),
        (right * 0.7).astype(np.float32)
    ]


def extract_4ch(audio_data: np.ndarray, sampleRate: int, target_sr: int = 44100) -> List[np.ndarray]:
    audio_data = resample(audio_data, sampleRate, target_sr)
    
    if len(audio_data.shape) == 1:
        mono = audio_data.astype(np.float32)
        return [mono.copy() for _ in range(4)]
    
    if audio_data.shape[1] == 1:
        mono = audio_data[:, 0]
        return [mono.copy() for _ in range(4)]
    
    if audio_data.shape[1] == 2:
        return stereo_to_4ch(audio_data[:, 0], audio_data[:, 1])
    
    if audio_data.shape[1] >= 4:
        return [audio_data[:, i].astype(np.float32) for i in range(4)]
    
    available = audio_data.shape[1]
    channels = []
    for i in range(4):
        channels.append(audio_data[:, i % available].astype(np.float32))
    
    min_length = min(len(ch) for ch in channels)
    return [ch[:min_length] for ch in channels]


def encode_pcm(channel: np.ndarray, bit_depth: int = 16) -> bytes:
    maxAmp = np.max(np.abs(channel))
    if maxAmp > 1.0:
        channel = channel / maxAmp
    
    if bit_depth == 16:
        return (channel * 32767.0).astype(np.int16).tobytes()
    else:
        pcm_data = (channel * 8388607.0).astype(np.int32)
        pcm_bytes = bytearray()
        for sample in pcm_data:
            pcm_bytes.extend(struct.pack('<i', sample)[:3])
        return bytes(pcm_bytes)


def process_mp3(input_file: str, sample_rate: int = 44100, bit_depth: int = 16) -> List[bytes]:
    audioData, original_sr = load_mp3(input_file)
    channels = extract_4ch(audioData, original_sr, sample_rate)
    return [encode_pcm(ch, bit_depth) for ch in channels]


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.mp3>")
        sys.exit(1)
    
    encoded_channels = process_mp3(sys.argv[1])
    
    print(f"Encoded 4 channels:")
    for i, data in enumerate(encoded_channels):
        print(f"  Channel {i+1}: {len(data)} bytes")
    
    print("\nReady for Bluetooth transmission")

