from random import randint
from functools import reduce
from copy import deepcopy
import typing

from improv.model import Model


__a = lambda text: f"a {text}" if text[0] not in 'aeioAEIO' else f"an {text}"
__A = lambda x: str.title(__a(x))
TEMPLATE_BUILTINS = {
    "a": __a,
    "an": __a,
    "A": __A,
    "An": __A,
    "cap": str.upper, # capitalizes all letters
    "tit": str.title, # capitalizes first leter of each word
}


class Improv:
    def __init__ (
            self, 
            snippets:dict, 
            reincorporate:bool=False, 
            persistence:bool=True,
            audit:bool=False,
            filters:list[typing.Callable]=[],
            builtins:dict={},
            salienceFormula:typing.Callable=lambda x: x,
            submodeler:typing.Callable=lambda model, subModelName: Model(),
            ):
        self.snippets:dict = {}
        # preprocess snippet tags
        for name, snippet in snippets.items():
            if type(snippet) is str: snippet = [snippet]
            if type(snippet) is list: snippet = {'groups': snippet}
            
            for g,group in enumerate(snippet['groups']):
                if type(group) is str: group = snippet['groups'][g] = {'phrases': group}
                if 'tags' not in group: group['tags'] = []
                if type(group['tags']) is str: group['tags'] = group['tags'].split(',')
                for t,tag in enumerate(group['tags']):
                    if type(tag) is str: group['tags'][t] = tag.strip().split(' ')
            
            self.snippets[name] = snippet
        self.reincorporate:bool = reincorporate
        self.persistence:bool = persistence
        self.audit:bool = audit
        self.builtins:dict = builtins
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
        
        self.__stack:list = []

        if audit:
            self.instantiateAuditData()
    
    ## PUBLIC METHODS
    
    def gen (self, snippetName:str, model:Model) -> str:
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
            assert type(submodel) is Model, ValueError(f'subModel "{subModelName}" must be Model type (was {type(submodel)})')
        else:
            submodel = self.submodeler(model, subModelName)
            setattr(model, subModelName, submodel)
        
        return submodel
    
    
    def clearHistory (self): self.history = []
    def clearTagHistory (self): self.tagHistory = []
    def clearAudit(self): 
        assert self.audit, ValueError('No audit to clear') 
        self.instantiateAuditData()
    
    def phraseAudit(self):
        assert self.audit, ValueError('No audit to view') 
        return deepcopy(self.__phraseAudit)
    
    def phraseStack(self): return deepcopy(self.__stack)
    
    
    ## PRIVATE METHODS
    
    def __gen(self, snippetName:str, model:Model, subModelName:str=None) -> str:
        '''
        Actually generate text. Separate from #gen() because we don't want to clear
        history or error-handling data while a call to #gen() hasn't finished
        returning
        
        For the sake of better error handling, we try to keep an accurate record
        of what snippet is being generated at any given time.
        '''
        if subModelName is not None:
            model = self.getSubModel(model, subModelName)
        
        if snippetName in model.bindings:
            return model.bindings[snippetName]
        
        # Keep a stack of snippets we are using while recurring.
        self.__stack.append(snippetName)
        
        if snippetName not in self.snippets:
            IndexError(f'Unknown snippet "{snippetName}"')
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
                    assert len(filterOutput)==2, ValueError(f"Filter {filter.__name__} returned {len(filterOutput)} values, must be 1 or 2")
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
        
        assert len(phrases) > 0, f"No phrases available in snippet {snippetName}"
        
        # Select a phrase at random.
        chosenPhrase, tags = phrases[randint(0, len(phrases)-1)]
        
        if self.reincorporate:
            model.mergeTags(tags)

        # Store amount of times each phrase is selected, for later debugging of statistics
        if self.audit:
            self.__phraseAudit[snippetName][chosenPhrase] += 1
        
        # Store history
        self.tagHistory.extend(tags)
        self.history.append(chosenPhrase)
        
        # Process the selected phrase for snippets (recursively)
        output = self.__template(chosenPhrase, model)
        
        # Bound snippets are fixed once generated (per model)
        if 'bind' in self.snippets[snippetName] and self.snippets[snippetName]['bind']:
            model.bindings[snippetName] = output
        
        self.__stack.pop() 
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
        
        # This is a literal directive.
        elif directive[0] == "'" and directive[-1] == "'":
            return directive[1, -1]
        
        # Snippet
        elif directive[0] == ':':
            return self.__gen(directive[1:], model)

        # Snippet using tags
        if directive[0] == '|' :
            try:
                tagStr, snippet = directive[1:].split(':', 1)
            except ValueError as e:
                raise Exception(f'Bad or malformed directive "{rawDirective}": expected :')
            
            newTag = tagStr.split('|')

            # copy current model and add tags
            newModel = deepcopy(model)
            newModel.mergeTags([newTag])

            # set bindings to same object, to receive new ones automatically
            newModel.bindings = model.bindings

            # store info, to perform reincorporation
            currTagPos = len(self.tagHistory)
            currAttrs = model.__dict__.keys()

            result = self.__gen(snippet, newModel)

            if self.reincorporate:
                # use tag history to reincorporate new tags and attrs from new model into current one
                numAddedTags = len(self.tagHistory) - currTagPos
                addedTags = self.tagHistory[-numAddedTags:]
                model.mergeTags(addedTags)
                for k, v in newModel.__dict__.items():
                    if k not in currAttrs:
                        setattr(model, k, v)

            return result
        
        # SubModel snippet
        elif directive[0] == '>':
            try:
                subModelName, subSnippet = directive[1:].split(':', 1)
            except ValueError as e:
                raise Exception(f'Bad or malformed directive "{rawDirective}": expected :')
            return self.__gen(subSnippet, model, subModelName)
        
        # Chained directive.
        elif directive.find(' ') != -1:
            funcName, rest = directive.split(' ', 1)
            
            # let's have the model take priority
            if (hasattr(model, funcName)
                    and callable(model.funcName)):
                func = model.funcName
            elif funcName in self.builtins:
                func = self.builtins[funcName]
            elif funcName in TEMPLATE_BUILTINS:
                func = TEMPLATE_BUILTINS[funcName]
            else:
                raise Exception(f'''Bad or malformed directive "{rawDirective}": 
                                builtin or model property "{funcName}" 
                                not found or not a function.''')
            
            return func(self.__processDirective(rest, model))
        
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
        
        # SubModel attribute
        elif directive.find('.') > 0:
            direcChain = directive.split('.')
            return reduce(lambda model, directive: getattr(model, directive), direcChain, model)
        
        # Unknown
        else:
            return '[' + directive + ']'
    
    def instantiateAuditData(self):
        self.__phraseAudit = {
            key: {
                phrase: 0
                for group in snippet['groups']
                for phrase in group['phrases']
            }

            for key, snippet in self.snippets.items()
        }