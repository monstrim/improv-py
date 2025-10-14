from random import randint
from improv.model import Model

class Improv:
    def __init__ (
            self, 
            snippets:dict, 
            ):
        self.snippets:dict = dict(snippets)
        
    ## PUBLIC METHODS
    
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
        chosenPhrase = phrases[randint(0, len(phrases)-1)]

        # Process the selected phrase for snippets (recursively)
        output = self.__template(chosenPhrase, model)
        
        # Bound snippets are fixed once generated (per model)
        if 'bind' in self.snippets[snippetName] and self.snippets[snippetName]['bind']:
            model.bindings[snippetName] = output
        
        return output
    
    
    def __template(self, phrase:str, model:Model) -> str:
        '''
        Processes phrase, detecting [directives] and sending them to processing
        '''
        openBracket = phrase.find('[')
        closeBracket = phrase.find(']')
        
        if openBracket == -1: return phrase
        if closeBracket == -1: raise Exception(f'Missing close bracket in phrase: {phrase}')
        
        before = phrase[: openBracket]
        directive = phrase[openBracket+1 : closeBracket]
        after = phrase[closeBracket+1 :]
        
        processed = self.__processDirective(directive, model)
        final = f'{before}{processed}{self.__template(after, model)}'
        
        return final
    
    
    def __processDirective (self, rawDirective:str, model:Model) -> str:
        '''
        Processes [directives], expanding them,
        reursively calling __gen() if needed
        '''
        directive = rawDirective.strip()
        
        if len(directive)==0: return ''
        
        # Snippet
        elif directive[0] == ':':
            return self.gen(directive[1:], model)
        
        # Unknown
        else:
            return '[' + directive + ']'
