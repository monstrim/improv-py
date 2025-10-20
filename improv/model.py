class Model:
    def __init__(self, tags=[], **kwargs):
        self.tags = []
        self.mergeTags(tags)
        self.bindings = {}

        for k,v in kwargs.items():
            assert not hasattr(self, k), f"Invalid argument {k}"
            setattr(self, k, v)
    
    
    def mergeTags (self, tags:list) -> None:
        if type(tags) is str:
            tags = tags.split(',')
        
        for tag in tags:
            if type(tag) is str:
                tag = tag.strip().split(' ')
            
            # Find the matching tag...
            matches = [
                i for i,v in enumerate(self.tags)
                if v[0] == tag[0]
            ]
        
            if len(matches)==0:
                self.tags.append(tag)
            else:
                i = matches[0]
                if len(tag) >= len(self.tags[i]):
                    self.tags[i] = list(tag)