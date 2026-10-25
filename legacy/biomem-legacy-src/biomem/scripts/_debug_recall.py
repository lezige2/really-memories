import tempfile, pathlib
from biomem.agent import Agent
from biomem.config import Settings
from biomem.llm import MockClient
s=Settings.load(data_dir=pathlib.Path(tempfile.mkdtemp()))
s.mock=True
a=Agent(s, llm=MockClient())
a.turn("我叫林澈，养了只猫叫团子，它特别爱拆家")
for c in a.store.list_cards(limit=10):
    print("CARD", c.id, c.kind, "|", c.text, "|", c.summary)
a.new_session()
cards, trace = a.recall_debug("你还记得我家那只猫叫什么吗？")
print("TRACE", trace.summary())
for c in cards:
    print("REC", c.card.id, round(c.score,2), c.card.text)
print("gated", a.metamemory.decide("你还记得我家那只猫叫什么吗？").explain())
a.close()
