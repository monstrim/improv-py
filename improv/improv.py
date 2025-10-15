from random import randint
import typing

from improv.model import Model

class Improv:
    def __init__ (
            self, 
            snippets:dict, 
            reincorporate:bool=False, 
            filters:list[typing.Callable]=[],
            ):
        self.snippets:dict = dict(snippets)
        self.reincorporate:bool = reincorporate
        self.filters:list[typing.Callable] = filters
        '''
        Filter functions should return None if the whole group is to be discarded,
        or a new group if the group has been altered (e.g some phrases filtered)
        '''
        
    ## PUBLIC METHODS
    
    def gen (self, snippetName:str, model:Model=None) -> str:
        if snippetName in model.bindings:
            return model.bindings[snippetName]
        
        groups = self.snippets[snippetName]['groups']
        
        # Filter, and score, snippet groups
        filteredGroups = []
        
        for group in groups:
            for filter in self.filters:
                group = filter(group, model, self)
                if group is None:
                    break
            
            if group is not None and len(group['phrases']) > 0:
                filteredGroups.append(group)
        
        # Flatten phrases in a list.
        phrases = [
            [phrase, group['tags']]
            for group in filteredGroups
            for phrase in group['phrases']
        ]
        
        # Select a phrase at random.
        chosenPhrase, tags = phrases[randint(0, len(phrases)-1)]
        
        if self.reincorporate:
            model.mergeTags(tags)

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
        
        # Random integer
        elif directive[0] == '#':
            try:
                a, b = directive[1:].split('-', 1)
            except:
                raise Exception(f'''Bad or malformed directive "{rawDirective}": expected -''')
            
            try:
                return randint(int(a), int(b))
            except:
                raise Exception(f'''Bad or malformed directive "{rawDirective}": 
                                cannot parse as integers: "{a}", "{b}".''')
        
        # Model attribute
        elif hasattr(model, directive):
            return getattr(model, directive)
        
        # Unknown
        else:
            return '[' + directive + ']'
