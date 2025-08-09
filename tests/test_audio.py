"""
This file tests the audio functionality.
Tests using the speaker and microphone have the tag manual.
Run those tests using 'pytest -m manual'.
"""
import os
import pytest
from sound2font.audiomodule import AudioData, Microphone, Speaker

def test_memory_behaviour():
    pass

@pytest.mark.manual
def test_microphone():
    pass

def test_audio_data():
    audio_data_en = AudioData.load("/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/audio_en.wav")
    audio_data_de = AudioData.load("/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/audio_de.wav")
    assert len(audio_data_en) > 0
    assert len(audio_data_de) > 0
    audio_data_en.extend(audio_data_de)
    assert len(audio_data_en) > len(audio_data_de)
    audio_data_en.save("/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/temp.wav")
    audio_data_temp = AudioData.load("/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/temp.wav")
    assert audio_data_temp == audio_data_en # __eq__ works because AudioData inherits from bytearray.
    os.remove("/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/temp.wav")

@pytest.mark.manual
def test_speaker():
    pass