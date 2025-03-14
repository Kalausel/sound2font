import time
import wave
from pyaudio import PyAudio, paInt16, paContinue

MIC_DEFAULTS = {
    "rate": 44100,
    "channels": 1,
    "format": paInt16,
    "input": True,
    "input_device_index": None,  # Use default device
    "frames_per_buffer": 1024
}

SPEAKER_DEFAULTS = {
    "rate": 44100,
    "channels": 1,
    "format": paInt16,
    "output": True,
    "output_device_index": None,  # Use default device
    "frames_per_buffer": 1024
}

class AudioData(bytearray):
    def __init__(self, sample_width: int, max_var_size: int = 5e7, max_file_size: int = 1e8):
        super().__init__()
        self.max_var_size = max_var_size
        self.max_file_size = max_file_size
        self.sample_width = sample_width

    @classmethod
    def load(cls, filename):
        with wave.open(filename, "rb") as wf:
            loaded = cls(sample_width=wf.getsampwidth())
            for _ in range(wf.getnframes()):
                loaded.extend(wf.readframes(1))
            return loaded

    def extend(self, in_data):
        self.check_size(in_data)
        super().extend(in_data)

    def check_size(self, data2):
        new_size = len(self) + len(data2)  # len(bytearray) is the actual size in bytes.
        if new_size > self.max_var_size:
            raise MemoryError(f"Maximum size of self.data would be exceeded.\n"
                              f"Max size: {self.max_var_size} Actual size: {new_size}\n"
                              "Did not append new chunk.")

    def save(self, filename, **input_kwargs):
        kwargs = dict(SPEAKER_DEFAULTS, **input_kwargs)
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(kwargs['channels'])
            wf.setsampwidth(self.sample_width)
            wf.setframerate(kwargs['rate'])
            wf.writeframes(self)  # Directly write bytearray

    def as_bytes(self):
        return bytes(self)  # Convert bytearray to immutable bytes object.

class Speaker:
    def __init__(self, **kwargs):
        self.kwargs = dict(SPEAKER_DEFAULTS, **kwargs)
        self.pyaudio = PyAudio()

    def play(self, audio: AudioData):
        if not audio:
            print("Warning: No audio data to play.")
            return
        
        stream = self.pyaudio.open(format=self.kwargs['format'],
                                   channels=self.kwargs['channels'],
                                   rate=self.kwargs['rate'],
                                   output_device_index=self.kwargs['output_device_index'],
                                   output=True)
        
        stream.start_stream()
        stream.write(audio.as_bytes())  # Convert bytearray to bytes before writing
        stream.stop_stream()
        stream.close()
    
    def __del__(self):
        self.pyaudio.terminate()

class Microphone:
    def __init__(self, **kwargs):
        self.kwargs = dict(MIC_DEFAULTS, **kwargs)
        self.pyaudio = PyAudio()
        self.sample_width = self.pyaudio.get_sample_size(self.kwargs['format'])
    
    def record(self, interval: float, destination: AudioData = None):
        do_return = False
        if destination is None:
            destination = AudioData(self.sample_width)
            do_return = True
        destination.sample_width = self.sample_width

        def audio_callback(in_data, frame_count, time_info, status):
            try:
                destination.extend(in_data)
                #print(time.perf_counter())
            except MemoryError as e:
                print("Error:", e)
                return (b'\x00' * len(in_data), paContinue)  # Return silence to prevent breakage
            return (in_data, paContinue)

        stream = self.pyaudio.open(**self.kwargs, stream_callback=audio_callback)
        stream.start_stream()

        start_time = time.perf_counter()
        while time.perf_counter() - start_time < interval:
            time.sleep(0.1)  # Prevent high CPU usage

        stream.stop_stream()
        stream.close()

        if do_return:
            return destination
    
    def __del__(self):
        self.pyaudio.terminate()
