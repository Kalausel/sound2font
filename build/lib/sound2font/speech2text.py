import os

from vosk import BatchModel, BatchRecognizer, Model, KaldiRecognizer
# KaldiRecognizer does real-time transcription. Potentially faster, less accurate.

from textmodule import TextData
from audiomodule import AudioData

MODEL_PATH = "./models"

class Speech2Text:
    def __init__(self, model_name: str, sample_rate: int
                 , model_type: str = "kaldi"):
        self.model_name = model_name
        self.sample_rate = sample_rate
        model_path = os.path.join(MODEL_PATH, self.model_name)
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