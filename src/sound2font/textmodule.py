# PUNCTS are punctuation characters. They need special treatment.
PUNCTS = ['.', '!', ',', '?', ":", ";"]
# DISCONNECTED_CHARS are characters that are not connected to its neighbours, even in a connected font.
DISCONNECTED_CHARS = PUNCTS + ["-", "'"] + [str(x) for x in range(10)]

class TextData_fw:
    # This literally only contains the text as a string, but I want backwards compatibility with vosk
    # , which returns a more complicated string.
    def __init__(self, fw_result: str):
        super().__init__()
        self.fw_result = fw_result
    
    def text(self):
        return self.fw_result