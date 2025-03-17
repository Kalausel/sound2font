import json
from matplotlib import pyplot as plt

PEN = {
    "UP": "M5",
    "DOWN": "M3",
    "PAUSE": "M7"
}

DISCONNECTED_CHARS = [".", ",", "!", "-", "'", "?", ":", ";"]

def get_coordinate(line: str, coord: str):
    if not coord in ["X", "Y"]:
        raise ValueError(f"Coordinate {coord} not recognised. Must be 'X' or 'Y'.")
    if coord not in line:
        return None
    return float(line.split(coord)[1].split(" ")[0])

def replace_coordinate(line: str, coord: str, new_value: float):
    old_value = get_coordinate(line, coord)
    if old_value is None:
        return line
    return line.replace(f"{coord}{old_value}", f"{coord}{new_value}")


class GCode:
    # This class stores Gcode commands.
    # I want the string to start with the command to go to the starting position.
    # Then pen down (or pen up, for that matter).
    # Every z movement and every x-y movement should be a separate line.
    
    def __init__(self, gcode: str):
        self.gcode = gcode

    def show(self):
        # This method plots the Gcode to a matplotlib plot.
        # TODO Arcs and curves
        pen_down = False
        # Calculate the number of pages needed.
        no_pages = 1
        for line in self.get_lines():
            if line == PEN["PAUSE"]:
                no_pages += 1
        _, axes = plt.subplots(no_pages // 2 + 1, 1 if no_pages == 1 else 2)
        last_x, last_y = 0, 0
        ax = axes[0]
        page = 1
        for line in self.get_lines():
            if line == PEN["UP"]:
                pen_down = False
            elif line == PEN["DOWN"]:
                pen_down = True
            elif line.startswith("G1") or line.startswith("G0"):
                style = "--" if line.startswith("G0") else "-"
                col = "b" if pen_down else "r"
                x = get_coordinate(line, "X")
                if "X" is None:
                    x = last_x
                y = get_coordinate(line, "Y")
                if "Y" is None:
                    y = last_y
                ax.plot([last_x, x], [last_y, y], f"{col}{style}")
                last_x, last_y = x, y
            elif line == PEN['PAUSE']:
                ax = axes[page]
                page += 1
            else:
                print(f"Warning: Unknown Gcode command {line}")
        plt.show()

    def translate(self, vector: tuple[float], inplace: bool = False) -> None:
        x, y = vector
        new_gcode = ""
        for line in self.gcode.split("\n"):
            if line.startswith("G1") or line.startswith("G0"):
                old_x = get_coordinate(line, "X")
                old_y = get_coordinate(line, "Y")
                new_gcode += replace_coordinate(replace_coordinate(line, "X", old_x+x), "Y", old_y+y) + "\n"
            else:
                new_gcode += line + "\n"
        if inplace:
            self.gcode = new_gcode
        else:
            return self.__class__(new_gcode)
    
    def clean(self, remove_duplicates: list = [PEN["UP"], PEN["DOWN"], PEN["PAUSE"]]
              , collapse_G0: bool = True):
        # Remove double G0 commands
        # Remove double Pen up or Pen down commands
        unclean = self.get_lines()
        rm_pens = []
        rm_G0s = []
        add_G0 = []
        for i, line in enumerate(unclean):
            if i == 0:
                continue
            if line in remove_duplicates and unclean[i-1] == line:
                rm_pens.append(i)
            if collapse_G0 and line.startswith('G0') and unclean[i-1].startswith('G0'):
                if i-1 in [x[0] for x in add_G0]:
                    rm_G0s.append(i)
                    add_x = get_coordinate(unclean[i], "X")
                    add_y = get_coordinate(unclean[i], "Y")
                    add_G0.append((i-1, add_x, add_y))
                else:
                    rm_G0s.append(i-1)
                    add_x = get_coordinate(unclean[i-1], "X")
                    add_y = get_coordinate(unclean[i-1], "Y")
                    add_G0.append((i, add_x, add_y))
        rm_ids = rm_pens + rm_G0s
        for i, x, y in add_G0:
            unclean[i] = replace_coordinate(unclean[i], "X", get_coordinate(unclean[i], "X") + x)
            unclean[i] = replace_coordinate(unclean[i], "Y", get_coordinate(unclean[i], "Y") + y)
        self.gcode = "\n".join([x for i, x in enumerate(unclean) if not i in rm_ids])

    def append(self, other: "GCode", inplace: bool = True):
        if inplace:
            self.gode += "\n" + other.gcode
        else:
            return self.__class__(self.gcode + "\n" + other.gcode)

    def get_lines(self):
        return self.gcode.split("\n")
    
    def add_command(self, command: str):
        self.gcode += "\n" + command

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.gcode)
    
    def load(cls, path: str):
        with open(path, "r") as f:
            return cls(f.read())

class Character:
    # Origin at bottom left
    # Default size = 1 (== height of A)
    # TODO Print i dots and Umlaut dots later.

    def __init__(self, gcode: GCode, width: float = None):
        self.gcode = gcode
        self.gcode.gcode = gcode.gcode.replace("PENUP", PEN["UP"]).replace("PENDOWN", PEN["DOWN"])
        if width is None:
            self.width = self.calculate_width()
        else:
            self.width = width
        self.final_position = self.find_final_position()

    def find_final_position(self):
        x = None
        y = None
        for line in self.gcode.get_lines().reversed():
            if x is None:
                x = get_coordinate(line, "X")
            if y is None:
                y = get_coordinate(line, "Y")
        if x is None:
            x = 0
        if y is None:
            y = 0
        return (x, y)

    def calculate_width(self):
        old_x = 0
        for line in self.gcode.get_lines():
            x = get_coordinate(line, "X")
            if x is not None and x > old_x:
                old_x = x
        return old_x
    
    def resize(self, factor):
        new_gcode = GCode("")
        for line in self.gcode.get_lines():
            x = get_coordinate(line, "X")
            y = get_coordinate(line, "Y")
            new_gcode.add_command(replace_coordinate(replace_coordinate(line, "X", x*factor), "Y", y*factor))
        self.gcode = new_gcode
        self.width *= factor
        self.final_position = self.find_final_position()

class Alphabet:
    
    def __init__(self, alphabet: dict[Character]):
        # self.alphabet = {'a': Character, 'b': Character ... '.': Character .... 'Z': Character}
        self.alphabet = alphabet
    
    def resize(self, factor: float):
        self.alphabet = {key: self.alphabet[key].resize(factor) for key in self.alphabet}

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.alphabet, f)
    
    def load(cls, path: str):
        with open(path, "r") as f:
            return cls(json.load(f))
