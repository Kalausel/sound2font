from warnings import warn
import json
from matplotlib.patches import Arc, PathPatch
from matplotlib.path import Path
from matplotlib import pyplot as plt
import numpy as np

from sound2font.textmodule import DISCONNECTED_CHARS, PUNCTS

PEN = {
    "UP": "G0 Z0",
    "DOWN": "G0 Z9",
    "PAUSE": "M7"
}

COORDS = ["X", "Y", "I", "J", "P", "Q"]

def get_coordinate(line: str, coord: str, return_str: bool = False):
    if not coord in COORDS:
        raise ValueError(f"Coordinate {coord} not recognised. Must be one of {COORDS}.")
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

def add_coordinate(line: str, coord: str, value: float) -> str:
    # Check that coordinate does not exist.
    if get_coordinate(line, coord) is not None:
        raise ValueError(f"add_coordinate: Coordinate {coord} already exists in line \"{line}\"")
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
        raise ValueError(f"add_coordinate: coord must be \"X\" or \"Y\". Received {coord}.")
    
def bezier_max(line: str, coord: str, start: tuple[float], steps: int = 1000, return_min: bool = False) -> float:
    if coord not in ["X", "Y"]:
        raise NotImplementedError
    idx = {"X": 0, "Y": 1}
    p12 = np.array([get_coordinate(line, "I"), get_coordinate(line, "J")])
    p43 = np.array([get_coordinate(line, "P"), get_coordinate(line, "Q")])
    start = np.array([start[0], start[1]])
    end = np.array([get_coordinate(line, "X"), get_coordinate(line, "Y")])
    P = [start, start + p12, end + p43, end]
    if not return_min:
        max_coord = 0
    else:
        min_coord = 100
    for t in np.linspace(0, 1, steps):
        new_coord = (1 - t)**3 * P[0] + 3 * (1 - t)**2 * t * P[1] + 3 * (1 - t) * t**2 * P[2] + t**3 * P[3]
        if not return_min and new_coord[idx[coord]] > max_coord:
            max_coord = new_coord[idx[coord]]
        elif return_min and new_coord[idx[coord]] < min_coord:
            min_coord = new_coord[idx[coord]]
    return max_coord if not return_min else min_coord

def circle_max(line: str, coord: str, start: tuple[float]) -> float:
    if coord != "X":
        raise NotImplementedError
    if not line.startswith('G2') and not line.startswith('G3'):
        raise ValueError(f"circle_max: Expecting line that starts with 'G2' or 'G3'. Got {line}")
    start = np.array(start)
    center = start + np.array([get_coordinate(line, "I"), get_coordinate(line, "J")])
    end = np.array([get_coordinate(line, "X"), get_coordinate(line, "Y")])
    radius = np.linalg.norm(start - center)
    thetas = [np.atan2(*np.flip(start-center)), np.atan2(*np.flip(end-center))]
    thetas = [(x * 180 / np.pi) for x in thetas] # Angles in the interval [-180, 180)
    if line.startswith('G2'): # If clockwise, make it counterclockwise.
        thetas = [x for x in reversed(thetas)]
    # If angle 0 is in the range, this is the maximum.
    if thetas[0] < 0 and thetas[1] > 0 or \
        all(np.sign(thetas) == 1) and thetas[0] > thetas[1] or \
        all(np.sign(thetas) == -1) and thetas[0] > thetas[1]:
        return center[0] + radius
    # If not, the maximum is at one of the arc's ends.
    else:
        return center[0] + radius * np.cos(np.min(np.abs(thetas)) * np.pi / 180)

def cubicbezier2gcode(start: 'np.array|list', end: 'np.array|list', start_angle: float, end_angle: float, curvature: tuple[float]) -> 'GCode':
    # Unit vectors
    # The curvature parameter describes the distance of the auxiliary points to their respective starting points, relative to the distance start-end.
    if isinstance(start, list):
        start = np.array(start)
    if isinstance(end, list):
        end = np.array(end)
    distance = np.linalg.norm(end - start)
    p12 = distance * curvature[0] * np.array([np.cos(start_angle), np.sin(start_angle)])
    p43 = (-1) * distance * curvature[1] * np.array([np.cos(end_angle), np.sin(end_angle)])
    return GCode(f"G5 I{p12[0]} J{p12[1]} P{p43[0]} Q{p43[1]} X{end[0]} Y{end[1]}")

def arc2g1(start: tuple[float], line: str, interval: float = 0.1) -> str:
    if not line.startswith('G2') and not line.startswith('G3'):
        raise ValueError(f"circle_max: Expecting line that starts with 'G2' or 'G3'. Got {line}")
    start = np.array(start)
    center = start + np.array([get_coordinate(line, "I"), get_coordinate(line, "J")])
    end = np.array([get_coordinate(line, "X"), get_coordinate(line, "Y")])
    radius = np.linalg.norm(start - center)
    thetas = [np.atan2(*np.flip(start-center)), np.atan2(*np.flip(end-center))] # Angles in the interval [-pi, pi)
    if line.startswith('G2') and thetas[0] < thetas[1]:
        thetas[0] += 2 * np.pi
    elif line.startswith('G3') and thetas[0] > thetas[1]:
        thetas[1] += 2 * np.pi
    arc_length = radius * np.abs(thetas[1] - thetas[0])
    num_steps = int(arc_length / interval)
    out_str = ""
    for i in range(num_steps):
        t = i / num_steps
        theta = thetas[0] + t * (thetas[1] - thetas[0])
        x = center[0] + radius * np.cos(theta)
        y = center[1] + radius * np.sin(theta)
        out_str += f"G1 X{x} Y{y}\n"
    out_str += f"G1 X{end[0]} Y{end[1]}"
    return out_str

def bezier2g1(start: tuple[float], line: str, interval: float = 0.1) -> str:
    p12 = np.array([get_coordinate(line, "I"), get_coordinate(line, "J")])
    p43 = np.array([get_coordinate(line, "P"), get_coordinate(line, "Q")])
    start = np.array([start[0], start[1]])
    end = np.array([get_coordinate(line, "X"), get_coordinate(line, "Y")])
    p23 = end + p43 - start - p12
    P = [start, start + p12, end + p43, end]
    max_steps = int((np.linalg.norm(p12) + np.linalg.norm(p43) + np.linalg.norm(p23)) / interval) + 1 # This should always be longer than the curve.
    out_str = ""
    t = 0
    for i in range(max_steps):
        if i == max_steps - 1:
            warn(f"bezier2g1: Reached maximum number of steps ({max_steps}).")
        dx_dt = np.linalg.norm(3 * ((1 - t)**2 * (P[1] - P[0]) + 2 * t * (1 - t) * (P[2] - P[1]) + t**2 * (P[3] - P[2])))
        t += interval / dx_dt
        if t > 1:
            break
        vector = (1 - t)**3 * P[0] + 3 * (1 - t)**2 * t * P[1] + 3 * (1 - t) * t**2 * P[2] + t**3 * P[3]
        x = vector[0]
        y = vector[1]
        out_str += f"G1 X{x} Y{y}\n"
    out_str += f"G1 X{end[0]} Y{end[1]}"
    return out_str

class GCode:
    # This class stores Gcode commands.
    # I want the string to start with the command to go to the starting position.
    # Then pen down (or pen up, for that matter).
    # Every z movement and every x-y movement should be a separate line.
    
    def __init__(self, commandstr: str):
        self.commandstr = commandstr

    def plot(self, subplot_size: tuple[float] = (6,6)
             , return_axes: bool = False
             , show: bool = True
             , show_moves: bool = True
             , show_control_points: bool = False
             , grid: bool = False
             , equal_aspect: bool = True
             , canvas_size: tuple[float] = None
             , title: str = None):
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
        last_line = None
        for idx, line in enumerate(self.get_lines()):
            if line.startswith("#") or line == "":
                continue # Ignore comments.
            elif line == PEN["UP"]:
                if idx != 0:
                    if last_line == PEN["DOWN"]:
                        ax.scatter([last_x], [last_y], c='b', marker='.')
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
                if line.startswith('G1') or line.startswith('G0') and show_moves:
                    ax.plot([last_x, x], [last_y, y], f"{col}{style}")
                last_x, last_y = x, y
            elif line.startswith("G2") or line.startswith("G3"):
                style =  "-"
                col = "b" if pen_down else "r"
                start = np.array([last_x, last_y])
                center = start + np.array([get_coordinate(line, "I"), get_coordinate(line, "J")])
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
            elif line.startswith('G5'):
                # Cubic Bezier curve
                style =  "-"
                col = "b" if pen_down else "r"
                p12 = np.array([get_coordinate(line, "I"), get_coordinate(line, "J")])
                p43 = np.array([get_coordinate(line, "P"), get_coordinate(line, "Q")])
                start = np.array([last_x, last_y])
                end = np.array([get_coordinate(line, "X"), get_coordinate(line, "Y")])
                verts = [start, start + p12, end + p43, end]
                codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
                path = Path(verts, codes)
                patch = PathPatch(path, facecolor='none', edgecolor=col)
                ax.add_patch(patch)
                ctrl_style = 'x--' if show_control_points else '-'
                lw = 2 if show_control_points else 0
                xs, ys = zip(*verts)
                ax.plot(xs, ys, ctrl_style, lw=lw, color='black', ms=10)
                last_x, last_y = end[0], end[1]
            elif line != PEN["PAUSE"]:
                print(f"Warning: Unknown Gcode command {line}")
            if line == PEN['PAUSE'] or idx == self.__len__() - 1:
                if equal_aspect:
                    ax.set_aspect('equal')
                if grid:
                    ax.grid()
                if title is not None:
                    ax.set_title(title)
                if canvas_size is not None:
                    ax.set_xlim(0, canvas_size[0])
                    ax.set_ylim(0, canvas_size[1])
                if no_pages <= 2 and line == PEN["PAUSE"]:
                    ax = axes[1]
                elif line == PEN["PAUSE"]:
                    ax = axes[page//2][page % 2]
                else:
                    pass
                page += 1
            last_line = line
        if show:
            plt.show()
        if return_axes:
            return axes
    
    def add_feed_rate(self, feed_rate: float, inplace: bool = False, overwrite: bool = False) -> None:
        # Add feed rate to every G1 command to avoid grbl error 22.
        new_commandstr = ""
        for line in self.commandstr.split("\n"):
            if line.startswith("G1"):
                new_line = line
                if "F" not in line:
                    new_line += f" F{feed_rate}"
                elif overwrite:
                    raise NotImplementedError("Overwriting previously defined feed rate not implemented.")
                    #new_line = replace_coordinate(new_line, "F", feed_rate)
                else:
                    pass
                new_commandstr += new_line + "\n"
            else:
                new_commandstr += line + "\n"
        if inplace:
            self.commandstr = new_commandstr
        else:
            return self.__class__(new_commandstr)

    def translate(self, vector: tuple[float], inplace: bool = False) -> None:
        new_commandstr = ""
        for line in self.commandstr.split("\n"):
            if line[0:2] in ["G0", "G1", "G2", "G3", "G5"]:
                new_line = line
                for coord in COORDS:
                    if line[0:2] in ["G2", "G3", "G5"] and coord not in ["X", "Y"]:
                        # In arcs and Bezier curves, I, J, P, Q are relative vectors, hence shall not be translated.
                        continue
                    old = get_coordinate(line, coord)
                    i = 0 if coord == "X" else 1
                    new_line = replace_coordinate(new_line, coord, old + vector[i] if old is not None else "dummy")
                new_commandstr += new_line + "\n"
            else:
                new_commandstr += line + "\n"
        if inplace:
            self.commandstr = new_commandstr
        else:
            return self.__class__(new_commandstr)
    
    def pure_code_str(self):
        # Remove empty lines and comments.
        rm_ids = []
        unclean = self.get_lines()
        for i, line in enumerate(unclean):
            if line.startswith("#") or line == "":
                rm_ids.append(i)
        clean = [x for i, x in enumerate(unclean) if not i in rm_ids]
        return "\n".join(clean)
    
    def check_limits(self, x_limits: tuple[float], y_limits: tuple[float]):
        for line in self.get_lines():
            if line.startswith("#") or line == "":
                continue
            x = get_coordinate(line, "X")
            y = get_coordinate(line, "Y")
            if x is not None and (x < x_limits[0] or x > x_limits[1]):
                raise ValueError(f"X coordinate {x} out of limits {x_limits}.")
            if y is not None and (y < y_limits[0] or y > y_limits[1]):
                raise ValueError(f"Y coordinate {y} out of limits {y_limits}.")
    
    def split_pages(self):
        # Split the Gcode into pages. A page is defined by a PEN["PAUSE"] command.
        # Returns a list of GCode objects.
        commandstr_list = self.commandstr.split(PEN["PAUSE"])
        gcode_list = [GCode(x) for x in commandstr_list]
        return gcode_list

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
        # Before collapsing the G0 commands, replace PENUP and PENDOWN commands because they also start with G0.
        semiclean = ['PENDOWN' if line == PEN["DOWN"] else 'PENUP' if line == PEN["UP"] else line for line in semiclean]
        rm_ids = []
        add_coords = []
        carry_x = None
        carry_y = None
        started = False
        for i, line in enumerate(semiclean):
            if line.startswith("#") or line == "":
                continue
            elif not started:
                started = True
            elif line.startswith('G0') and last_line.startswith('G0'):
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
            elif not line.startswith('G0'):
                carry_x = None
                carry_y = None
            elif line.startswith('G0'):
                pass
            else:
                warn(f"GCode.clean(): Line {line} not expected.")
            last_line = line
            last_idx = i
        commented = [x if not i in rm_ids else "# " + x + " CLEANED" for i, x in enumerate(semiclean)]
        for tup in add_coords:
            idx, coord, value = tup
            if not commented[idx].startswith("#"):
                commented[idx] = add_coordinate(commented[idx], coord, value)
        commented = [PEN["DOWN"] if line == 'PENDOWN' else PEN['UP'] if line == 'PENUP' else line for line in commented]
        self.commandstr = "\n".join(x for x in commented)

    def invert_coordinate(self, direction: int, inplace: bool = False) -> "GCode":
        # One variable is mirrored along the other axis.
        new_commandstr = ""
        for line in self.commandstr.split("\n"):
            if line[0:2] in ["G0", "G1", "G2", "G3", "G5"] and not line in [PEN["UP"], PEN["DOWN"]]:
                new_line = line
                old_coords = {}
                for coord in COORDS:
                    old = get_coordinate(line, coord)
                    if old is not None:
                        old_coords[coord] = old
                for coord in old_coords.keys():
                    new_coord = old_coords[coord]
                    if direction == 0 and coord in ["X", "I", "P"]:
                        new_coord = (-1) * old_coords[coord]
                    elif direction == 1 and coord in ["Y", "J", "Q"]:
                        new_coord = old_coords[correspondent] * np.sin(angle) + old_coords[coord] * np.cos(angle)
                    new_line = replace_coordinate(new_line, coord, new_coord)
                new_commandstr += new_line + "\n"
            else:
                new_commandstr += line + "\n"
        if inplace:
            self.commandstr = new_commandstr
        else:
            return self.__class__(new_commandstr)

    def rotate(self, angle: float, inplace: bool = False) -> "GCode":
        # Rotate the Gcode around the center point by angle degrees. Counterclockwise.
        # The center point is (0,0)
        angle = angle * np.pi / 180
        new_commandstr = ""
        for line in self.commandstr.split("\n"):
            if line[0:2] in ["G0", "G1", "G2", "G3", "G5"] and not line in [PEN["UP"], PEN["DOWN"]]:
                new_line = line
                old_coords = {}
                for coord in COORDS:
                    old = get_coordinate(line, coord)
                    if old is not None:
                        old_coords[coord] = old
                for coord in old_coords.keys():
                    if coord in ["X", "I", "P"]:
                        correspondent = "Y" if coord == "X" else "J" if coord == "I" else "Q"
                        old_correspondent = old_coords[correspondent] if correspondent in old_coords else carry[correspondent]
                        new_coord = old_coords[coord] * np.cos(angle) - old_correspondent * np.sin(angle)
                        if not correspondent in old_coords:
                            new_correspondent = old_coords[coord] * np.sin(angle) - carry[correspondent] * np.cos(angle)
                            new_line = add_coordinate(new_line, correspondent, new_correspondent)
                    elif coord in ["Y", "J", "Q"]:
                        correspondent = "X" if coord == "Y" else "I" if coord == "J" else "P"
                        old_correspondent = old_coords[correspondent] if correspondent in old_coords else carry[correspondent]
                        new_coord = old_correspondent * np.sin(angle) + old_coords[coord] * np.cos(angle)
                        if not correspondent in old_coords:
                            new_correspondent = carry[correspondent] * np.cos(angle) - old_coords[coord] * np.sin(angle)
                            new_line = add_coordinate(new_line, correspondent, new_correspondent)
                    new_line = replace_coordinate(new_line, coord, new_coord)
                new_commandstr += new_line + "\n"
                carry = {co: old_coords[co] if co in old_coords else carry[co] for co in ["X", "Y"]}
            else:
                new_commandstr += line + "\n"
        if inplace:
            self.commandstr = new_commandstr
        else:
            return self.__class__(new_commandstr)
    
    def curves2g1(self, interval: float = 0.1, inplace: bool = False) -> None:
        # Replaces G2 and G3 commands with G1 commands.
        first = True
        new_commandstr = ""
        for line in self.commandstr.split("\n"):
            if line[0:2] in ["G0", "G1", "G2", "G3", "G5"] and not line in [PEN["UP"], PEN["DOWN"]]:
                if first:
                    # First line must be G0 or G1.
                    if line[0:2] not in ["G0", "G1"]:
                        raise ValueError("The first Gcode command must be G0 or G1.")
                    start = np.array([get_coordinate(line, "X"), get_coordinate(line, "Y")])
                    if start[0] is None or start[1] is None:
                        raise ValueError("The first G0 or G1 command must have X and Y coordinates.")
                    first = False
                if line[0:2] in ["G2", "G3"]:
                    new_commandstr += arc2g1(start, line, interval) + "\n"
                elif line[0:2] == "G5":
                    new_commandstr += bezier2g1(start, line, interval) + "\n"
                else:
                    new_commandstr += line + "\n"
                new_x = get_coordinate(line, "X")
                new_y = get_coordinate(line, "Y")
                start = np.array([new_x if new_x is not None else start[0], new_y if new_y is not None else start[1]])
            else:
                new_commandstr += line + "\n"
        if inplace:
            self.commandstr = new_commandstr
        else:
            return self.__class__(new_commandstr)
    
    def last_position(self):
        x = None
        y = None
        for line in self.get_lines():
            if line[0:2] in ["G0", "G1", "G2", "G3", "G5"] and not line in [PEN["UP"], PEN["DOWN"]]:
                x = get_coordinate(line, "X")
                y = get_coordinate(line, "Y")
        return (x, y)


    def append(self, other: "GCode", inplace: bool = True):
        if inplace:
            self.commandstr += "\n" + other.commandstr
        else:
            return self.__class__(self.commandstr + "\n" + other.commandstr)

    def get_lines(self, skip_comments: bool = False):
        if not skip_comments:
            return self.commandstr.split("\n")
        else:
            return [x for x in self.commandstr.split("\n") if not x.startswith("#")]
    
    def add_command(self, command: str, comment: str = None):
        if comment is not None:
            if command in [PEN["DOWN"], PEN["UP"]]:
                warn(f"Did not add comment because command is {command}. This comment could interfere in GCode.clean().")
            else:
                self.commandstr += "\n# " + comment
        self.commandstr += "\n" + command

    def __len__(self):
        # Returns number of lines
        return self.commandstr.count("\n") + 1
    
    def __eq__(self, other):
        # Comments are on extra lines.
        # This equality operator only works on two cleaned GCode objects. It expects standard format.
        result = True # until proven otherwise.
        if self.commandstr == other.commandstr:
            return result
        sugo = [x for x in self.get_lines() if not x.startswith("#") and not x == ""]
        other_sugo = [x for x in other.get_lines() if not x.startswith("#") and not x == ""]
        for line, otherline in zip(sugo, other_sugo):
            if line == otherline:
                continue
            else:
                for coord in COORDS:
                    if coord in line and coord in otherline:
                        thisx = get_coordinate(line, coord)
                        otherx = get_coordinate(otherline, coord)
                        if not np.isclose(thisx, otherx):
                            result = False
                    elif coord not in line and coord not in otherline:
                        continue
                    else:
                        result = False
        return result

    def save(self, path: str, pure: bool = False):
        with open(path, "w") as f:
            if pure:
                f.write(self.pure_code_str())
            else:
                f.write(self.commandstr)
    
    @classmethod
    def load(cls, path: str):
        with open(path, "r") as f:
            return cls(f.read())

class Character:
    # Origin at bottom left
    # Default size = 1 (== height of A)
    # TODO Print i dots and Umlaut dots later.

    def __init__(self, gcode: GCode, width: float = None):
        self.gcode = gcode
        self.gcode.commandstr = gcode.commandstr.replace("PENUP", PEN["UP"]).replace("PENDOWN", PEN["DOWN"])
        if width is None:
            self.width = self.calculate_width()
        else:
            self.width = width
        self.final_position = self.find_final_position()
        self.final_angle = self.find_final_angle() # None for many characters.

    def connect(self, initial_position: tuple[float], initial_angle: float) -> GCode:
        # This method returns a modified GCode to suit the desired boundary conditions
        # set by the preceding character in a connected font.
        # I am setting up the characters such that the first segment can be replaced.
        # 1) Find the final position and angle of the first segment.
        line = None
        for i, l in enumerate(self.gcode.get_lines()):
            if l.startswith('G5'):
                line = l
                first_line = i
                break
        if line is None:
            raise NotImplementedError(f"sound2font.writemodule.Character.connect() is only implemented for connected characters starting with 'G5'.")
        p34 = (-1) * np.array([get_coordinate(line, "P"), get_coordinate(line, "Q")])
        final_angle = np.atan2(*np.flip(p34))
        final_position = [get_coordinate(line, "X"), get_coordinate(line, "Y")]
        new_line = cubicbezier2gcode(initial_position, final_position, initial_angle, final_angle, (0.3, 0.3)).commandstr
        return GCode("\n".join([new_line] + self.gcode.get_lines()[first_line+1:]))

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
    
    def find_final_angle(self):
        for line in reversed(self.gcode.get_lines()):
            if line.startswith("#") or line in ["", PEN["DOWN"], PEN["UP"]]:
                continue
            if line.startswith('G2') or line.startswith('G3'):
                center = np.array([get_coordinate(line, "I"), get_coordinate(line, "J")])
                end = np.array([get_coordinate(line, "X"), get_coordinate(line, "Y")])
                theta = np.atan2(*np.flip(end-center))
                if line.startswith('G2'): # clockwise
                    return theta - np.pi / 2
                else: # anti-clockwise
                    return theta + np.pi / 2
            if line.startswith('G5'):
                p34 = (-1) * np.array([get_coordinate(line, "P"), get_coordinate(line, "Q")])
                return np.atan2(*np.flip(p34))
        return None

    def calculate_width(self):
        # This is technically the maximum x.
        # But letters all start at x=0.
        # If they reach x<0 in the middle, the maximum x is still the relevant quantity.
        # I will ignore inner points of Bezier curves because this will entail a large effort with no tangible benefit.
        # In any case, for connected fonts, we really care about the endpoint.
        old_x = 0
        cursor = (0,0)
        for line in self.gcode.get_lines():
            x = None
            if line.startswith('G0'):
                x = get_coordinate(line, "X")
                cur_y = get_coordinate(line, "Y")
                cursor = (x if x is not None else cursor[0], cur_y if cur_y is not None else cursor[1])
            elif line.startswith('G1'):
                x = get_coordinate(line, "X")
                cur_y = get_coordinate(line, "Y")
                cursor = (x if x is not None else cursor[0], cur_y if cur_y is not None else cursor[1])
            elif line.startswith('G2') or line.startswith('G3'):
                x = circle_max(line, "X", start=cursor)
                cursor = (get_coordinate(line, "X"), get_coordinate(line, "Y"))
            elif line.startswith('G5'):
                # From Bezier curce, just analyse the endpoints. The endpoint of the letter should be the max x point anyway.
                x = get_coordinate(line, "X")
                cur_y = get_coordinate(line, "Y")
                cursor = (x if x is not None else cursor[0], cur_y if cur_y is not None else cursor[1])
            if x is not None and x > old_x:
                old_x = x
        return old_x
    
    def resize(self, factor):
        new_gcode = GCode("")
        for line in self.gcode.get_lines():
            new_line = line
            for coord in COORDS:
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
    
    def save_strings(self, path: str):
        with open(path, "w") as f:
            str_dict = {key: self.symbols[key].gcode.commandstr for key in self.symbols}
            json.dump(str_dict, f)
    
    @classmethod
    def load(cls, path: str):
        with open(path, "r") as f:
            return cls(json.load(f))
    
    @classmethod
    def load_from_string_dict(cls, path: str):
        with open(path, "r") as f:
            str_dict = json.load(f)
        return cls({key: Character(GCode(string)) for key, string in str_dict.items()})
