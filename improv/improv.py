from random import randint
from improv.model import Model

class Improv:
    def __init__ (
            self, 
            snippets:dict, 
            ):
        self.snippets:dict = dict(snippets)
        
    
    def gen (self, snippetName:str, model:Model=None) -> str:
        if snippetName in model.bindings:
            return model.bindings[snippetName]
        
        groups = self.snippets[snippetName]['groups']
        
        # Flatten phrases in a list.
        phrases = [
            phrase
            for group in groups
            for phrase in group['phrases']
        ]
        
        # Select a phrase at random.
        output = phrases[randint(0, len(phrases)-1)]
        
        # Bound snippets are fixed once generated (per model)
        if 'bind' in self.snippets[snippetName] and self.snippets[snippetName]['bind']:
            model.bindings[snippetName] = output
        
        return output