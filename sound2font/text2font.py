from warnings import warn
import json

from sound2font.writemodule import WritingData, Page

class Text2Font:

    def __init__(self, font_path):
        self.font_path = font_path
        with open(font_path, "r") as f:
            self.alphabet = json.load(f)

    def convert(self, text: str, page: Page) -> WritingData:
        gcode = ""
        paragraphs = text.split("\n")
        no_paragraphs = len(paragraphs)
        for i, paragraph in enumerate(paragraphs):
            if i != 0 or paragraph == "":
                page.new_line()
            for word in paragraph.split(" "):
                gcode += page.add_word(word)
            if i == no_paragraphs - 1 and paragraph == "":
                page.new_line()
        return WritingData(gcode)