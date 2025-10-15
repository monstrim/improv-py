from enum import Enum


class TagComparison(Enum):
    NONE = 0
    PARTIAL = 1
    MISMATCH = 2
    TOTAL = 3


def __compareTags (a:list, b:list) -> TagComparison:
    if a[0]!=b[0]: return TagComparison.NONE
    if a==b: return TagComparison.TOTAL
    for (x,y) in zip(a,b):
        if x != y: return TagComparison.MISMATCH
    return TagComparison.PARTIAL


def mismatchFilter ():
    '''
    Looks for mismatched tags (i.e., tags which match the first position, and are therefore equivalent,
    but with a different sub-tag).
    '''
    def _fn(group, model, improv):
        for groupTag in group['tags']:
            for modelTag in model.tags:
                if __compareTags(groupTag, modelTag) == TagComparison.MISMATCH:
                    return None
        return group

    return _fn
