import json
from matplotlib.patches import Arc
from matplotlib import pyplot as plt
import numpy as np

PEN = {
    "UP": "M5",
    "DOWN": "M3",
    "PAUSE": "M7"
}

DISCONNECTED_CHARS = [".", ",", "!", "-", "'", "?", ":", ";"]

def get_coordinate(line: str, coord: str, return_str: bool = False):
    if not coord in ["X", "Y", "I", "J"]:
        raise ValueError(f"Coordinate {coord} not recognised. Must be 'X' or 'Y'.")
    if coord not in line:
        return None
    if return_str:
        return line.split(coord)[1].split(" ")[0]
    return float(line.split(coord)[1].split(" ")[0])

def replace_coordinate(line: str, coord: str, new_value: float):
    old_value = get_coordinate(line, coord, return_str=True)
    if old_value is None:
        return line
    return line.replace(f"{coord}{old_value}", f"{coord}{new_value}")

def add_coord(line: str, coord: str, value: float) -> str:
    # Check that coordinate does not exist.
    if get_coordinate(line, coord) is not None:
        raise ValueError(f"add_coord: Coordinate {coord} already exists in line \"{line}\"")
    if coord == "X":
        # Insert x into the line.
        return line.split("Y")[0] + f"X{value} Y" + line.split("Y")[1]
    elif coord == "Y":
        # Insert y into the line.
        # Find first space after X
        space_idx = line.find(" ", line.find("X"))
        if space_idx == -1:
            space_idx = len(line)
        return line[:space_idx] + f" Y{value}" + line[space_idx:]
    else:
        raise ValueError(f"add_coord: coord must be \"X\" or \"Y\". Received {coord}.")


class GCode:
    # This class stores Gcode commands.
    # I want the string to start with the command to go to the starting position.
    # Then pen down (or pen up, for that matter).
    # Every z movement and every x-y movement should be a separate line.
    
    def __init__(self, gcode: str):
        self.gcode = gcode

    def show(self, subplot_size: tuple[float] = (6,6)):
        # This method plots the Gcode to a matplotlib plot.
        # TODO Arcs and curves
        pen_down = False
        # Calculate the number of pages needed.
        no_pages = 1
        for line in self.get_lines():
            if line == PEN["PAUSE"]:
                no_pages += 1
        no_rows = (no_pages + 1) // 2
        _, axes = plt.subplots(no_rows, 1 if no_pages == 1 else 2, figsize=(no_pages*subplot_size[0], no_rows*subplot_size[1]))
        last_x, last_y = 0, 0
        if no_pages == 1:
            ax = axes
        elif no_pages <= 2:
            ax = axes[0]
        else:
            ax = axes[0][0]
        page = 1
        for line in self.get_lines():
            if line.startswith("#"):
                continue # Ignore comments.
            if line == PEN["UP"]:
                pen_down = False
            elif line == PEN["DOWN"]:
                pen_down = True
            elif line.startswith("G1") or line.startswith("G0"):
                style = "--" if line.startswith("G0") else "-"
                col = "b" if pen_down else "r"
                x = get_coordinate(line, "X")
                if x is None:
                    x = last_x
                y = get_coordinate(line, "Y")
                if y is None:
                    y = last_y
                ax.plot([last_x, x], [last_y, y], f"{col}{style}")
                last_x, last_y = x, y
            elif line.startswith("G2") or line.startswith("G3"):
                style =  "-"
                col = "b" if pen_down else "r"
                center = np.array([get_coordinate(line, "I"), get_coordinate(line, "J")])
                start = np.array([last_x, last_y])
                end = np.array([get_coordinate(line, "X"), get_coordinate(line, "Y")])
                radius = np.linalg.norm(start - center)
                thetas = [np.atan2(*np.flip(start-center)), np.atan2(*np.flip(end-center))]
                thetas = [x * 180 / np.pi for x in thetas]
                if line.startswith("G2"): # clockwise
                    thetas = [x for x in reversed(thetas)]
                # Arc draws counterclockwise starting at (1,0)
                arc = Arc((center[0], center[1]), 2*radius, 2*radius
                          , theta1=thetas[0], theta2=thetas[1]
                          , edgecolor=col, linestyle=style, fill=False)
                ax.add_patch(arc)
                last_x, last_y = end[0], end[1]
            elif line == PEN['PAUSE']:
                if no_pages <= 2:
                    ax = axes[1]
                else:
                    ax = axes[page//2][page % 2]
                page += 1
            elif line == '':
                pass
            else:
                print(f"Warning: Unknown Gcode command {line}")
        plt.show()

    def translate(self, vector: tuple[float], inplace: bool = False) -> None:
        new_gcode = ""
        for line in self.gcode.split("\n"):
            if line[0:2] in ["G0", "G1", "G2", "G3"]:
                new_line = line
                for coord in ["X", "Y", "I", "J"]:
                    old = get_coordinate(line, coord)
                    i = 0 if coord in ["X", "I"] else 1
                    new_line = replace_coordinate(new_line, coord, old + vector[i] if old is not None else "dummy")
                new_gcode += new_line + "\n"
            else:
                new_gcode += line + "\n"
        if inplace:
            self.gcode = new_gcode
        else:
            return self.__class__(new_gcode)
    
    def clean(self):
        # Comment instead of remove.
        # 1) Remove PENUP if already up and PENDOWN if already down.
        # 2) Remove successive G0 commands. Ignore comments and empty lines.
        #    Carry coordinates, if not explicitly specified in the new line.
        unclean = self.get_lines()
        rm_ids = []
        pen_down = None
        for i, line in enumerate(unclean):
            if line in [PEN["DOWN"], PEN["UP"]]:
                if pen_down is not None:
                    if pen_down and line == PEN["DOWN"] or not pen_down and line == PEN["UP"]:
                        rm_ids.append(i)
                pen_down = True if line == PEN["DOWN"] else False
        semiclean = [x if not i in rm_ids else "# " + x + " CLEANED" for i, x in enumerate(unclean)]
        rm_ids = []
        add_coords = []
        carry_x = None
        carry_y = None
        for i, line in enumerate(semiclean):
            if i == 0:
                last_line = line
                last_idx = 0
                continue
            if line.startswith("#") or line == "":
                continue
            if line.startswith('G0') and last_line.startswith('G0'):
                last_x, last_y = get_coordinate(last_line, "X"), get_coordinate(last_line, "Y")
                new_x, new_y = get_coordinate(line, "X"), get_coordinate(line, "Y")
                if new_x is None:
                    if last_x is not None:
                        carry_x = last_x
                        add_coords.append((i, "X", last_x))
                    elif carry_x is not None:
                        add_coords.append((i, "X", carry_x))
                if new_y is None:
                    if last_y is not None:
                        carry_y = last_y
                        add_coords.append((i, "Y", last_y))
                    elif carry_y is not None:
                        add_coords.append((i, "Y", carry_y))
                rm_ids.append(last_idx)
            if not line.startswith('G0') and last_line.startswith('G0'):
                carry_x = None
                carry_y = None
            last_line = line
            last_idx = i
        commented = [x if not i in rm_ids else "# " + x + " CLEANED" for i, x in enumerate(semiclean)]
        for tup in add_coords:
            idx, coord, value = tup
            if not commented[idx].startswith("#"):
                commented[idx] = add_coord(commented[idx], coord, value)
        self.gcode = "\n".join(x for x in commented)
        

    def append(self, other: "GCode", inplace: bool = True):
        if inplace:
            self.gcode += "\n" + other.gcode
        else:
            return self.__class__(self.gcode + "\n" + other.gcode)

    def get_lines(self):
        return self.gcode.split("\n")
    
    def add_command(self, command: str, comment: str = None):
        if comment is not None:
            self.gcode += "\n# " + comment
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
        for line in reversed(self.gcode.get_lines()):
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
            new_line = line
            for coord in ["X", "Y", "I", "J"]:
                old = get_coordinate(line, coord)
                new_line = replace_coordinate(new_line, coord, old*factor if old is not None else "dummy")
            new_gcode.add_command(new_line)
        self.gcode = new_gcode
        self.width *= factor
        self.final_position = self.find_final_position()

class Alphabet:
    
    def __init__(self, symbols: dict[Character]):
        # self.symbols = {'a': Character, 'b': Character ... '.': Character .... 'Z': Character}
        self.symbols = symbols
    
    def resize(self, factor: float):
        for key in self.symbols:
            self.symbols[key].resize(factor)

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.symbols, f)
    
    @classmethod
    def load(cls, path: str):
        with open(path, "r") as f:
            return cls(json.load(f))
    
    @classmethod
    def load_from_string_dict(cls, path: str):
        with open(path, "r") as f:
            str_dict = json.load(f)
        return cls({key: Character(GCode(string)) for key, string in str_dict.items()})
