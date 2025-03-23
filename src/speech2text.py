import os

from vosk import BatchModel, BatchRecognizer, Model, KaldiRecognizer
# KaldiRecognizer does real-time transcription. Potentially faster, less accurate.

from sound2font.textmodule import TextData
from sound2font.audiomodule import AudioData

class Speech2Text:
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