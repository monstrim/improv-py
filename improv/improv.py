from improv.model import Model

class Improv:
    def __init__ (
            self, 
            snippets:dict, 
            ):
        self.snippets:dict = dict(snippets)
        
    
    def gen (self, snippetName:str, model:Model=None) -> str:
        output = ...
        
        return output