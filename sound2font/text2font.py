from warnings import warn
import json

from sound2font.writemodule import Alphabet, GCode, PEN, DISCONNECTED_CHARS

class Text2Font:
    # Origin at top left

    def __init__(self, width: float, height: float
                 , font_path: str, gap_between_chars: bool
                 , font_size: float, line_spacing: float
                 , char_spacing: float = 0
                 , space_ratio: float = 0.4
                 , initial_position: tuple[float, float] = None
                 , string_alphabet: bool = False
                 #, trailing_char_spacing: bool = False
    ):
        self.width = width
        self.height = height
        self.font_size = font_size
        self.line_spacing = line_spacing
        if initial_position is None:
            self.initial_position = (0, height - font_size) # Lower edge of first line
        else:
            self.initial_position = initial_position
        self.current_position = self.initial_position
        self.char_spacing = char_spacing
        self.font_size = font_size
        self.space_width = space_ratio * font_size
        self.font_path = font_path
        self.gap_between_chars = gap_between_chars
        if string_alphabet:
            self.alphabet = Alphabet.load_from_string_dict(font_path)
        else:
            self.alphabet = Alphabet.load(font_path)
        self.alphabet.resize(font_size)
        self.pen_down = False

    def convert(self, text: str, clean: bool = True) -> GCode:
        gcode = GCode(PEN["UP"]) # Make sure that the pen is up at the start.
        gcode.add_command(f"G0 X{self.current_position[0]} Y{self.current_position[1]}", comment="Move to initial position")
        #paragraphs = text.split("\n")
        #no_paragraphs = len(paragraphs)
        #for i, paragraph in enumerate(paragraphs):
        for i, paragraph in enumerate(text.split("\n")):
            if paragraph == "":
                gcode.add_command(self.new_line(), comment="New line because start of explicit newline character")
            if i != 0:
                gcode.add_command(self.new_line(), comment="New line because start of new paragraph") # Changes self.current_position and adds G0 move.
            for j, word in enumerate(paragraph.split(" ")):
                # Add a space before every word.
                # If the paragraph starts with a space, or ends with a space, this is caught by word == "".
                # A space will be added accordingly.
                # This does not check for necessary newlines or newpages. However, this will be caught
                # at the next word. The G0 movement outside the page will finally be removed in gcode.clean().
                if j != 0 or word == "":
                    self.current_position = (self.current_position[0] + self.space_width,
                                             self.current_position[1])
                    gcode.add_command(f"G0 X{self.current_position[0]} Y{self.current_position[1]}"
                                      , comment="Space before word" if j!=0 else "Space due to explicit space character")
                # Appends GCode until the end of the last character. This may be different from self.current_position!
                # Changes self.current_position to the beginning of the non-existing next character, i.e. the beginning of the "space" character.
                gcode.append(self.add_word(word, first_word=(j==0)))
            # The below two lines seem like they should not be here.
            # if i == no_paragraphs - 1 and paragraph == "":
            #     gcode.add_command(self.new_line())
        if clean:
            gcode.clean()
        return gcode

    def add_word(self, word: str, first_word: bool = False) -> GCode:
        # 1) Check whether to start a new line.
        # 2) Check whether to start a new page.
        # 3) Add gcode accordingly.
        # This does not add spaces. These are treated as characters.
        gcode = GCode("")
        required_space = sum([self.alphabet.symbols[char].width + self.char_spacing for char in word])
        available_space = self.width - self.current_position[0]
        # If the first word in the paragraph does not fit in the line,
        # the word will be split up rather than a new line added.
        if available_space >= required_space or first_word:
            pass
        else:
            gcode.add_command(self.new_line(), comment="New line because line has not enough space left for next word")
            if self.current_position[1] < 0:
                # Adds gcode (pause) and G0 move, and sets self.current_position to 0,self.font_size
                gcode.add_command(self.new_page(), comment="New page because next line would exeed y-limit")
        for char in word:
            # Adds GCode and changes current position until beginning of new char.
            # In the case of connected fonts, this is the end of the current char.
            gcode.add_command(self.gcode_and_move_cursor(char), comment=f"{char}")
        #gcode.add_command(f"G0 X{self.current_position[0] + self.space_width}")
        return gcode
    
    def gcode_and_move_cursor(self, char: str) -> str:
        # 1) Calculate the next character's starting position
        next_char_pos = (self.current_position[0] + self.alphabet.symbols[char].width + self.char_spacing, self.current_position[1])
        # Split up the word if it is longer than a whole line.
        if next_char_pos[0] - self.char_spacing > self.width:
            commandstr = "# New line within word because the character does not have enough space left\n" + self.new_line() + "\n"
            if self.current_position[1] < 0:
                commandstr += "# New page within word because the character does not have enough space left\n" + self.new_page() + "\n"
            next_char_pos = (self.current_position[0] + self.alphabet.symbols[char].width + self.char_spacing, self.current_position[1])
        else:
            commandstr = ""
        # If not self.gap_between_chars, next_char_pos == char.final_position.
        # If this is not the case, the code will work, but the first line of the next char will be wrong.
        # This is probably okay for cursive font. Characters can have slightly different starting positions.
        # 2) Add the gcode command string
        commandstr += self.alphabet.symbols[char].gcode.translate(self.current_position).gcode
        if self.gap_between_chars or char in DISCONNECTED_CHARS:
            # 3) Add G0 movement to the next character's starting position.
            commandstr = PEN['UP'] + "\n" + commandstr
            commandstr += "\n" + (PEN["UP"])
            self.pen_down = False
            commandstr += "\n" + (f"G0 X{next_char_pos[0]} Y{next_char_pos[1]}")
            # 4) Set current position to the previously calculated next character's starting position.
            self.current_position = next_char_pos
        return commandstr

    def new_line(self):
        self.current_position = (0, self.current_position[1] - self.line_spacing - self.font_size)
        self.pen_down = False
        return PEN["UP"] + f"\nG0 X0 Y{self.current_position[1]}"

    def new_page(self):
        self.current_position = (0, self.height - self.font_size)
        self.pen_down = False
        return PEN['UP'] + f"\nG0 X0 Y{self.current_position[1]}\n" + PEN['PAUSE']

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.__dict__, f)
    
    def load(cls, path: str):
        with open(path, "r") as f:
            return cls(**json.load(f))
