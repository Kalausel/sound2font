from warnings import warn
import json

from sound2font.textmodule import DISCONNECTED_CHARS, PUNCTS
from sound2font.writemodule import Alphabet, GCode, PEN, cubicbezier2gcode

class Text2Font:
    # Origin at top left

    def __init__(self, width: float, height: float
                 , font_path: str, connected: bool
                 , font_size: float, line_spacing: float
                 , char_spacing: float = 0
                 , space_ratio: float = 0.25
                 , initial_position: tuple[float, float] = None
                 , string_alphabet: bool = False
                 , punct_spacing: float = None
    ):
        self.width = width
        self.height = height
        self.font_size = font_size
        self.line_spacing = line_spacing
        if initial_position is None:
            self.initial_position = (0, height - font_size) # Lower edge of first line
        else:
            self.initial_position = initial_position
        # self.current_position is changes in Y only integer lines.
        self.current_position = self.initial_position
        self.char_spacing = char_spacing
        if self.char_spacing == 0 and punct_spacing is None:
            self.punct_spacing = 0.2 * font_size
        else:
            self.punct_spacing = punct_spacing
        self.font_size = font_size
        self.space_width = space_ratio * font_size
        self.font_path = font_path
        self.connected = connected
        if string_alphabet:
            self.alphabet = Alphabet.load_from_string_dict(font_path)
        else:
            self.alphabet = Alphabet.load(font_path)
        self.alphabet.resize(font_size)
        self.pen_down = False

    def convert(self, text: str, clean: bool = True) -> GCode:
        """
        Do not pass strings like " ", "\n", "\n\n" to this method.
        Use Text2font.newline() instead.
        Do not add spaces manually.
        """
        gcode = GCode(PEN["UP"]) # Make sure that the pen is up at the start.
        gcode.add_command(f"G0 X{self.current_position[0]} Y{self.current_position[1]}", comment="Move to initial position")
        for i, paragraph in enumerate(text.split("\n")):
            if paragraph == "":
                # Triggers, when paragraph starts or ends with '\n'.
                gcode.add_command(self.new_line().commandstr, comment="New line because start of explicit newline character")
                continue
            if i != 0:
                gcode.add_command(self.new_line().commandstr, comment="New line because start of new paragraph") # Changes self.current_position and adds G0 move.
            for j, word in enumerate(paragraph.split(" ")):
                # Add a space before every word.
                # If the paragraph starts with a space, or ends with a space, this is caught by word == "".
                # A space will be added accordingly.
                # This does not check for necessary newlines or newpages. However, this will be caught
                # at the next word. The G0 movement outside the page will finally be removed in GCode.clean().
                if j != 0 or word == "":
                    self.current_position = (self.current_position[0] + self.space_width,
                                             self.current_position[1])
                    gcode.add_command(self.add_space().commandstr, comment="Space before word" if j!=0 else "Space due to explicit space character")
                # Appends GCode until the end of the last character. This may be different from self.current_position!
                # Changes self.current_position to the beginning of the non-existing next character, i.e. the beginning of the "space" character.
                gcode.append(self.add_word(word, first_word=(j==0)))
        # Add a space at the end. I know no case, where this is not needed or irrelevant.
        gcode.add_command(self.add_space().commandstr, comment="Space at the end of Text2Font.convert()")
        if clean:
            gcode.clean()
        return gcode
    
    def add_space(self, comment: str = None):
        self.current_position = (self.current_position[0] + self.space_width, self.current_position[1])
        return GCode(f"G0 X{self.current_position[0]} Y{self.current_position[1]}")

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
            gcode.add_command(self.new_line().commandstr, comment="New line because line has not enough space left for next word")
            if self.current_position[1] < 0:
                # Adds gcode (pause) and G0 move, and sets self.current_position to 0,self.font_size
                gcode.add_command(self.new_page().commandstr, comment="New page because next line would exceed y-limit")
        last_char = None
        for char in word:
            # Adds GCode and changes current position both until beginning of new char.
            # In the case of connected fonts, this is the end of the current char.
            gcode.add_command(self.gcode_and_move_cursor(char, last_char=last_char), comment=f"Char {char}")
            last_char = char
        if self.connected: # Otherwise, PENUP is already added in self.gcode_and_move_cursor().
            gcode.add_command(PEN["UP"])
        return gcode
    
    def gcode_and_move_cursor(self, char: str, last_char: str = None) -> str:
        # 1) Calculate the next character's starting position
        if char in PUNCTS and self.punct_spacing is not None:
            self.current_position = (self.current_position[0] - self.char_spacing + self.punct_spacing, self.current_position[1])
            next_char_pos = (self.current_position[0] + self.alphabet.symbols[char].width + self.punct_spacing, self.current_position[1])
        else:
            next_char_pos = (self.current_position[0] + self.alphabet.symbols[char].width + self.char_spacing, self.current_position[1])
        
        # Split up the word if it is longer than a whole line.
        new = False
        if not char in PUNCTS and next_char_pos[0] - self.char_spacing + self.alphabet.symbols["-"].width > self.width:
            new = True
            commandstr = self._add_hyphen().commandstr
            commandstr += "\n# New line within word because the character does not have enough space left\n" + self.new_line().commandstr + "\n"
            if self.current_position[1] < 0:
                commandstr += "# New page within word because the character does not have enough space left\n" + self.new_page().commandstr + "\n"
            next_char_pos = (self.current_position[0] + self.alphabet.symbols[char].width + self.char_spacing, self.current_position[1])
        elif char in PUNCTS:
            commandstr = f"G0 X{self.current_position[0]} Y{self.current_position[1]}"
        else:
            commandstr = ""
        # If self.connected, next_char_pos == char.final_position.
        # If this is not the case, the code will work, but the first line of the next char will be wrong.
        # This is probably okay for cursive font. Characters can have slightly different starting positions.
        # 2) Add the gcode command string
        if self.connected and last_char is not None and not last_char in DISCONNECTED_CHARS and not char in DISCONNECTED_CHARS and not new:
            commandstr += self.alphabet.symbols[char].connect([0, self.alphabet.symbols[last_char].final_position[1]]
                                                              , self.alphabet.symbols[last_char].final_angle).translate(self.current_position).commandstr
        else:
            commandstr += self.alphabet.symbols[char].gcode.translate(self.current_position).commandstr
        if not self.connected or char in DISCONNECTED_CHARS:
            # 3) Add G0 movement to the next character's starting position. Only if disconnected.
            commandstr = PEN['UP'] + "\n" + commandstr
            commandstr += "\n" + (PEN["UP"])
            self.pen_down = False
            commandstr += "\n" + (f"G0 X{next_char_pos[0]} Y{next_char_pos[1]}")
        # 4) Set current position to the previously calculated next character's starting position (bottom).
        self.current_position = next_char_pos
        return commandstr
    
    def _add_hyphen(self):
        # Only use before newline() or newpage(). Otherwise, use "-" in your input text.
        # Add hyphen at most until the edge of the writing area.
        # Otherwise, this could fail for large fonts and small writing areas.
        # However, such a case should be caught after the font generation.
        distance_to_edge = self.width - self.current_position[0]
        hyphen_length = self.alphabet.symbols["-"].width
        if hyphen_length < distance_to_edge:
            gcode = self.alphabet.symbols["-"].gcode
        else:
            gcode = GCode(f"G0 X0 Y0.5\n{PEN['DOWN']}\nG1 X{distance_to_edge} Y0.5\n{PEN['UP']}")
        commandstr = gcode.translate(self.current_position).commandstr
        # Wait at the end of the hyphen in PENUP position. Next will be a newline() or newpage()
        commandstr = PEN['UP'] + "\n" + commandstr
        commandstr += "\n" + (PEN["UP"])
        self.pen_down = False
        return GCode(commandstr)

    def new_line(self):
        self.current_position = (0, self.current_position[1] - self.line_spacing - self.font_size)
        self.pen_down = False
        return GCode(PEN["UP"] + f"\nG0 X0 Y{self.current_position[1]}")

    def new_page(self):
        self.current_position = (0, self.height - self.font_size)
        self.pen_down = False
        return GCode(PEN['UP'] + f"\nG0 X0 Y{self.current_position[1]}\n" + PEN['PAUSE'])

    def reset_cursor(self):
        self.current_position = (0, self.height - self.font_size)

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.__dict__, f)
    
    def load(cls, path: str):
        with open(path, "r") as f:
            return cls(**json.load(f))
