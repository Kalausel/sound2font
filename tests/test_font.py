import os
import numpy as np

from sound2font.writemodule import GCode, Alphabet

GCODE_PATH = "/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/test_gcode"
ALPHABET_PATH = "/home/klaus/.local/lib/python3.12/site-packages/sound2font/tests/test_data/test_alphabet.json"

def test_gcode():
    gcode = GCode.load(GCODE_PATH)
    gcode.save('temp')
    loaded = GCode.load('temp')
    assert gcode == loaded
    os.remove('temp')
    gcode = GCode("G0 X1 Y2\nG0 X3\nG0 Y1\nG1 X4 Y7")
    gcode.clean()
    print(f"CLEANED CODE: {gcode.commandstr}")  
    assert gcode == GCode("G0 X3 Y1\nG1 X4 Y7")
    gcode.translate((1,2), inplace=True)
    assert gcode == GCode("G0 X4 Y3\nG1 X5 Y9")
    gcode.plot(show=False)

def test_alphabet():
    alphabet = Alphabet.load_from_string_dict(ALPHABET_PATH)
    char = alphabet.symbols['A']
    char_width = char.width
    alphabet.resize(2)
    scaled_char = alphabet.symbols['A']
    print(f"{scaled_char.width}\n{char.width}")
    assert np.isclose(2 * char_width, scaled_char.width)
