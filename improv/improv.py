from random import randint
import typing

from improv.model import Model

class Improv:
    def __init__ (
            self, 
            snippets:dict, 
            filters:list[typing.Callable]=[],
            ):
        self.snippets:dict = dict(snippets)
        self.filters:list[typing.Callable] = filters
        '''
        Filter functions should return None if the whole group is to be discarded,
        a single value for scoring if the whole group is accepted, and a list of 
        [value, new group] if the group has been altered (e.g some phrases filtered)
        '''
        
    ## PUBLIC METHODS
    
    def gen (self, snippetName:str, model:Model=None) -> str:
        if snippetName in model.bindings:
            return model.bindings[snippetName]
        
        groups = self.snippets[snippetName]['groups']
        
        # Filter, and score, snippet groups
        filteredGroups = []
        maxScore = float('-inf')
        
        for group in groups:
            score = 0
            
            for filter in self.filters:
                filterOutput = filter(group, model, self)
                
                if filterOutput is None:
                    group = None
                    break
                elif type(filterOutput) in (list, tuple):
                    # We got a tuple, meaning the filter wants to modify the group before
                    # moving on.
                    assert len(filterOutput)==2, "Filter must return 1 or 2 values"
                    scoreOffset, group = filterOutput
                else:
                    scoreOffset = filterOutput
                
                score += scoreOffset
            
            if group is not None and len(group['phrases']) > 0:
                filteredGroups.append({'group': group, 'score': score})
                maxScore = max(score, maxScore)
        
        # Filter out groups based on score threshold
        scoredGroups = [g['group'] for g in filteredGroups if g['score'] >= maxScore]
        
        # Flatten phrases in a list.
        phrases = [
            phrase
            for group in scoredGroups
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
