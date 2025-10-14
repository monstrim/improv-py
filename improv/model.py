class Model:
    def __init__(self, tags=[], **kwargs):
        self.tags = list(tags)
        self.bindings = {}

        for k,v in kwargs.items():
            assert not hasattr(self, k), f"Invalid argument {k}"
            setattr(self, k, v)
