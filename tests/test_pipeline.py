"""
This test tests the different modules' integration.
It does not check the outputs' accuracy.
"""
import pytest

from sound2font.audiomodule import AudioData, MIC_DEFAULTS
from sound2font.speech2text import Speech2Text
from sound2font.textmodule import GrammarAdder

CONVERTER_EN_MODEL_PATH = "/home/klaus/Documents/models/vosk/vosk-model-small-en-us-0.15"
CONVERTER_DE_MODEL_PATH = "/home/klaus/Documents/models/vosk/vosk-model-small-de-0.15"
GRAMMER_ADDER_EN_MODEL_PATH = "/home/klaus/Documents/models/vosk/vosk-recasepunc-en-0.22/checkpoint"
GRAMMER_ADDER_DE_MODEL_PATH = "/home/klaus/Documents/models/vosk/vosk-recasepunc-de-0.21/checkpoint"

audio_en = AudioData.load("/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/audio_en.wav")
audio_de = AudioData.load("/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/audio_de.wav")

@pytest.mark.parametrize("converter_model_path, audio, lang, grammar_model_path"
                        , [(CONVERTER_EN_MODEL_PATH
                        , audio_en, "en"
                        , GRAMMER_ADDER_EN_MODEL_PATH)
                        , (CONVERTER_DE_MODEL_PATH
                        , audio_de, "de"
                        , GRAMMER_ADDER_DE_MODEL_PATH)]
                        )
def test_pipeline(converter_model_path, audio, lang, grammar_model_path):
    converter = Speech2Text(converter_model_path, MIC_DEFAULTS['rate'])
    raw_text = converter.transcribe(audio)
    grammar_adder = GrammarAdder(grammar_model_path, language=lang)
    prediction = grammar_adder.add_grammar_rcp(raw_text.text())
    assert isinstance(prediction, str)
    assert len(prediction) > 0
    assert "#" not in prediction
    assert prediction[0] != " "
    assert prediction[-1] != " "