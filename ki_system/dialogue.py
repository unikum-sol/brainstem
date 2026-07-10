from dataclasses import dataclass
from ki_system.search import answer
from ki_system.wiki_quality import normalize_topic_from_question
@dataclass
class DialogueResult:
    topic:str; response:str; sources:list; data:dict
class DialogueManager:
    def __init__(self,memory): self.memory=memory
    def respond(self,text):
        res=answer(self.memory,text); topic=normalize_topic_from_question(text)
        try:
            self.memory.add_conversation('user',text,topic); self.memory.add_conversation('assistant',res.get('answer',''),topic); self.memory.set_topic_context(topic,text,res.get('sources',[]))
        except Exception: pass
        return DialogueResult(topic,res.get('answer',''),res.get('sources',[]),res)
