import pytest
from sound2font.textmodule import GrammarAdder, TextData

raw_text_en = TextData('{"result" : [{"text" : "does the fact that she is funny but still wants my money make her my honey or am i wrong anyway let us investigate"}]}')
raw_text_de = TextData('{"result" : [{"text" : "warum ist die banane krumm das wasser nass und der hammer nicht franz heisst die kanaille"}]}')
result_en = "Does the fact that she is funny but still wants my money make her my honey or am I wrong? Anyway, let us investigate."
result_de = "Warum ist die Banane krumm, das Wasser nass und der Hammer nicht? Franz heisst die Kanaille."

@pytest.mark.parametrize("text, result, lang, grammar_model_path"
                        , [(raw_text_en, result_en, "en"
                        , "/home/klaus/Documents/models/vosk/vosk-recasepunc-en-0.22/checkpoint")
                        , (raw_text_de, result_de, "de"
                        , "/home/klaus/Documents/models/vosk/vosk-recasepunc-de-0.21/checkpoint")]
                        )
def test_grammar(text, result, lang, grammar_model_path):
    grammar_adder = GrammarAdder(grammar_model_path, lang)
    prediction = grammar_adder.add_grammar_rcp(text.text())
    #assert prediction == result

@pytest.mark.parametrize("text"
                        , [(raw_text_en), (raw_text_de)])
def test_text_data(text):
    assert len(text.text()) > 0
    assert isinstance(text.text(), str)