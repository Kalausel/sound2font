from recasepunc.recasepunc import CasePuncPredictor, punctuation, punctuation_syms

# PUNCTS are punctuation characters. They need special treatment.
PUNCTS = ['.', '!', ',', '?', ":", ";"]
# DISCONNECTED_CHARS are characters that are not connected to its neighbours, even in a connected font.
DISCONNECTED_CHARS = PUNCTS + ["-", "'"] + [str(x) for x in range(10)]

class GrammarAdder:
    """
    Adds punctuation to an uncapitalised and unpunctuated text.
    faster_whisper already does this, so it is only needed for vosk.
    recasepunc is not very accurate, and has a model >1GB for each language.
    """

    def __init__(self, model_path: str, language: str):
        self.punctuator = CasePuncPredictor(model_path, lang=language)

    def add_grammar_rcp(self, input: str) -> str:
        output = ""
        for token_with_meta in self.punctuator.predict(input):
            if not token_with_meta[0].startswith("##"):
                output += " "
            if token_with_meta[1] == 'CAPITALIZE':
                output += token_with_meta[0].capitalize()
            elif token_with_meta[1] == 'UPPER':
                output += token_with_meta[0].upper()
            elif token_with_meta[1] == 'LOWER':
                output += token_with_meta[0].lower()
            elif token_with_meta[1] == 'OTHER':
                output += token_with_meta[0]
            else:
                raise ValueError(f"Unknown case type {token_with_meta[1]}")
            output += punctuation_syms[punctuation[token_with_meta[2]]]
            output = output.strip()
        return output.replace("##", "")

class TextData:

    def __init__(self, vosk_result: str):
        super().__init__()
        self.vosk_result = vosk_result
    
    def text(self):
        if len(self.vosk_result) > 12:
            return self.vosk_result.split('text" : "')[1][:-3]
        else:
            return ""

class TextData_fw:
    # This literally only contains the text as a string, but I want backwards compatibility with vosk
    # , which returns a more complicated string.
    def __init__(self, fw_result: str):
        super().__init__()
        self.fw_result = fw_result
    
    def text(self):
        return self.fw_result