import os
import numpy as np
import io
import soundfile as sf
from sound2font.audiomodule import MIC_DEFAULTS

from vosk import BatchModel, BatchRecognizer, Model, KaldiRecognizer
# KaldiRecognizer does real-time transcription. Potentially faster, less accurate.

from faster_whisper import WhisperModel

from sound2font.textmodule import TextData, TextData_fw
from sound2font.audiomodule import AudioData

class Speech2Text_vosk:
    def __init__(self, model_path: str, sample_rate: int
                 , model_type: str = "kaldi"):
        self.model_path = model_path
        self.sample_rate = sample_rate
        if model_type == "batch":
            model = BatchModel(model_path)
            self.recognizer = BatchRecognizer(model
                                            , self.sample_rate
                                            )
        elif model_type == "kaldi":
            model = Model(model_path)
            self.recognizer = KaldiRecognizer(model
                                            , self.sample_rate
                                            )
        else:
            raise ValueError(f"Model type {model_type} no recognised.\n" + \
                             "Available model types: 'batch', 'kaldi'")
        self.recognizer.SetWords(True)

    def transcribe(self, audio_data: AudioData) -> TextData:
        self.recognizer.AcceptWaveform(audio_data.as_bytes())
        return TextData(self.recognizer.Result())

class Speech2Text_fw:
    def __init__(self, model_size: str = "tiny", sample_rate: int = MIC_DEFAULTS["rate"], language: str = "en"):
        self.language = language
        if not self.language in ["en", "de"]:
            raise ValueError(f"Got language {self.language}.\n" + \
                             "Available languages: 'en', 'de'")
        if model_size not in ["tiny", "base", "small"]:
            raise ValueError(f"Model size {model_size} must be one of 'tiny' and 'base' and 'small'.")
        self.model = WhisperModel(model_size, compute_type="int8", cpu_threads=os.cpu_count()-1)
        self.sample_rate = sample_rate
    
    def transcribe(self, audio_data: AudioData) -> TextData:
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        buffer = io.BytesIO()
        sf.write(buffer, audio_np, samplerate=self.sample_rate, format="WAV")
        buffer.seek(0)
        segments, info = self.model.transcribe(buffer, language=self.language)
        return TextData_fw("".join([segment.text for segment in segments]))

Speech2Text = Speech2Text_vosk
