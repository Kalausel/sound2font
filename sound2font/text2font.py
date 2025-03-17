from warnings import warn
import json

from sound2font.writemodule import Alphabet, GCode, PEN, DISCONNECTED_CHARS

class Text2Font:

    def __init__(self, font_path):
        self.font_path = font_path
        with open(font_path, "r") as f:
            self.alphabet = json.load(f)

    

class Text2Font:
    # Origin at top left

    def __init__(self, width: float, height: float
                 , font_path: str, gap_between_chars: bool
                 , font_size: float, line_spacing: float
                 , char_spacing: float = 0
                 , initial_position: tuple[float, float] = None
                 #, trailing_char_spacing: bool = False
    ):
        self.width = width
        self.height = height
        self.font_size = font_size
        self.line_spacing = line_spacing
        if initial_position is None:
            self.initial_position = (0, 0 + font_size) # Lower edge of first line
        else:
            self.initial_position = initial_position
        self.current_position = initial_position
        self.char_spacing = char_spacing
        self.font_size = font_size
        self.font_path = font_path
        self.gap_between_chars = gap_between_chars
        self.alphabet = Alphabet.load(font_path)
        self.alphabet.resize(font_size)
        self.pen_down = False

    def convert(self, text: str) -> GCode:
        gcode = GCode("")
        paragraphs = text.split("\n")
        no_paragraphs = len(paragraphs)
        for i, paragraph in enumerate(paragraphs):
            if i != 0 or paragraph == "":
                self.new_line() # Changes self.current_position and adds G0 move.
            for word in paragraph.split(" "):
                # Appends GCode
                # Changes self.current_position
                gcode.append(self.add_word(word))
            if i == no_paragraphs - 1 and paragraph == "":
                self.new_line()
        gcode.clean()
        return gcode

    def add_word(self, word: str) -> str:
        gcode = GCode("")
        required_space = sum([self.alphabet[char].width + self.char_spacing for char in word])
        available_space = self.width - self.current_position[0]
        if available_space >= required_space:
            pass
        else:
            self.gcode.add_command(self.new_line())
            if self.current_position[1] > self.height:
                # Adds gcode (pause) and G0 move, and sets self.current_position to 0,self.font_size
                gcode.add_command(self.new_page())
        for char in word:
            # Adds GCode and changes current position until end of char (not until beginning of new char)
            gcode.add_command(self.gcode_and_move_cursor(char))
        return gcode
    
    def gcode_and_move_cursor(self, char: str) -> str:
        # TODO Handle trailing space at the end of a word.
        next_char_pos = (self.current_position[0] + self.alphabet[char].width + self.char_spacing, self.current_position[1])
        # If not self.gap_between_chars, next_char_pos == char.final_position.
        # If this is not the case, the code will work, but the first line of the next char will be wrong.
        commandstr = self.alphabet[char].gcode.translate(self.current_position).gcode
        self.current_position = next_char_pos
        if self.gap_between_chars or char in DISCONNECTED_CHARS:
            commandstr = PEN['UP'] + "\n" + commandstr
            commandstr += "\n" + (PEN["UP"])
            self.pen_down = False
            gcode += "\n" + (f"G0 X{next_char_pos[0]} Y{next_char_pos[1]}")
            self.current_position = next_char_pos
        return commandstr

    def new_line(self):
        self.current_position = (0, self.current_position[1] + self.line_spacing)
        self.pen_down = False
        return PEN["UP"] + f"\nG0 X0 Y{self.current_position[1]}"

    def new_page(self):
        self.current_position = (0, self.font_size)
        self.pen_down = False
        return PEN['UP'] + f"\nG0 X0 Y{self.current_position[1]}\n" + PEN['PAUSE']

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.__dict__, f)
    
    def load(cls, path: str):
        with open(path, "r") as f:
            return cls(**json.load(f))
