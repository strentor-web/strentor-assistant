"""Held-out question check: 37 differently-worded questions NOT used to tune the app.

Run:  python scripts/eval_questions.py        (uses whatever backend .env selects: extractive, Ollama or Claude)
Each question has expected keywords; the 3 off-topic questions must be refused.
Offline extractive mode scores about 76% (28/37); a generative backend is what handles free paraphrase.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import service  # noqa: E402

service.seed_public_kb()
service.load_samples()
# (question, any-of expected substrings in the lower-cased answer; None = must be refused)
T=[
("what's the founder's background","para powerlifter|certified"),
("who am i going to be training with","aditya|coach"),
("is this only for people in chairs","wheelchair"),
("can a total newbie join","beginner|assessment|start"),
("what do I need to buy before starting","equipment|minimal|band"),
("will I need a gym membership","equipment|home|gym"),
("how many times a week do I train","3, 4 or 5|sessions per week"),
("what is the minimum number of sessions per week","minimum|3"),
("how many weeks is it","12 weeks"),
("is it a monthly subscription","one-time|not a monthly|monthly"),
("what does one session cost in india","1,000|500"),
("cheaper option?","500|self-paced"),
("can I do it on my own schedule","self-paced|asynchronous"),
("do I get live coaching","trainer-led|live"),
("what happens after the programme ends","circle"),
("tell me about circle membership","circle|membership"),
("what is the free thing on the site","assessment|free"),
("do you offer a one time consult","strategy session"),
("how long is the strategy session","60 minutes|one-hour|one hour"),
("is the 7 day thing still sold","no longer"),
("do you have elite plan","no longer|elite"),
("which countries do you serve","india|uae|singapore"),
("can someone in London join","international|selected"),
("do you work with companies and NGOs","corporate|ngo"),
("can my employer sponsor this","corporate|csr"),
("do you give medical advice","medical|clinician|not"),
("can you cure my condition","cure|not|medical"),
("is there a refund","refund|policy|contact|don't have"),
("how do I pay","payment|razorpay|paypal|don't have"),
("can a family member be part of the first call","family"),
("are you a physiotherapist","physio|not|trainer"),
("what makes strentor different","wheelchair|founder|chair"),
("what is break build become","break"),
("how do I get in touch","contact|email|form|aditya"),
("what is the weather in mumbai today",None),
("who won the cricket world cup",None),
("write me a poem about cats",None),
]
ok=0
for q,exp in T:
    r=service.ask(q,"client"); a=r["answer"].lower()
    refused=a.startswith("i don't have") or a.startswith("blocked") or "i could not" in a
    if exp is None: good=refused
    else: good=(not refused or "don't have" in exp) and any(e in a for e in exp.split("|"))
    ok+=good
    if not good: print("MISS:",q,"->",a[:140].replace("\n"," | "))
print(f"{ok}/{len(T)}")
