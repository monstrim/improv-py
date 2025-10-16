from random import randint
import typing

from improv.model import Model

class Improv:
    def __init__ (
            self, 
            snippets:dict, 
            reincorporate:bool=False, 
            persistence:bool=True,
            filters:list[typing.Callable]=[],
            salienceFormula:typing.Callable=lambda x: x,
            submodeler:typing.Callable=lambda model, subModelName: Model(),
            ):
        self.snippets:dict = dict(snippets)
        self.reincorporate:bool = reincorporate
        self.persistence:bool = persistence
        self.salienceFormula:typing.Callable = salienceFormula
        self.submodeler:typing.Callable = submodeler
        
        self.history:list = []
        self.tagHistory:list = []
        self.filters:list[typing.Callable] = filters
        '''
        Filter functions should return None if the whole group is to be discarded,
        a single value for scoring if the whole group is accepted, and a list of 
        [value, new group] if the group has been altered (e.g some phrases filtered)
        '''
    
    ## PUBLIC METHODS
    
    def gen (self, snippetName:str, model:Model=None) -> str:
        '''
        Generate text (user-facing API). Since this function can recur, most of
        the heavy lifting is done in __gen().
        '''
        
        output = self.__gen(snippetName, model)
        
        if not self.persistence:
            self.clearHistory()
            self.clearTagHistory()
        
        return output
    
    
    def getSubModel (self, model:Model, subModelName:str) -> Model:
        '''
        A SubModel is just an attribute of a Model that is itself a Model.
        This function gets it by name, creating a new one if needed.

        Submodeler function can be added to Improv instance on init, to e.g. seed 
        the SubModel with tags from the parent, or otherwise depending on name.
        '''
        if hasattr(model, subModelName):
            submodel = getattr(model, subModelName)
        else:
            submodel = self.submodeler(model, subModelName)
            setattr(model, subModelName, submodel)
        
        return submodel
    
    
    def clearHistory (self): self.history = []
    def clearTagHistory (self): self.tagHistory = []
    
    ## PRIVATE METHODS
    
    def __gen(self, snippetName:str, model:Model, subModelName:str=None) -> str:
        '''
        Actually generate text. Separate from #gen() because we don't want to clear
        history or error-handling data while a call to #gen() hasn't finished
        returning
        
        For the sake of better error handling, we try to keep an accurate record
        of what snippet is being generated at any given time.
        '''
        if snippetName in model.bindings:
            return model.bindings[snippetName]
        
        if subModelName is not None:
            model = self.getSubModel(model, subModelName)
        
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
        scoreThreshold = self.salienceFormula(maxScore)
        scoredGroups = [g['group'] for g in filteredGroups if g['score'] >= scoreThreshold]
        
        # Flatten phrases in a list.
        phrases = [
            [phrase, group['tags']]
            for group in scoredGroups
            for phrase in group['phrases']
        ]
        
        # Select a phrase at random.
        chosenPhrase, tags = phrases[randint(0, len(phrases)-1)]
        
        if self.reincorporate:
            model.mergeTags(tags)
        
        # Store history
        self.tagHistory.extend(tags)
        self.history.append(chosenPhrase)
        
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
            return self.__gen(directive[1:], model)
        
        # SubModel snippet
        elif directive[0] == '>':
            try:
                subModelName, subSnippet = directive[1:].split(':', 1)
            except ValueError as e:
                raise Exception(f'Bad or malformed directive "{rawDirective}": expected :')
            return self.__gen(subSnippet, model, subModelName)
        
        
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
