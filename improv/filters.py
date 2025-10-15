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


def __groupComparer(comparisonMode, bonus:int, cumulative:bool=False):
    '''
    bonus=None eliminates groups, e.g. for mismatched filter. bonus can be negative for penalizing.
    '''
    def _fn(group, model, improv):
        score = 0
        for groupTag in group['tags']:
            for modelTag in model.tags:
                if __compareTags(groupTag, modelTag) == comparisonMode:
                    if not cumulative or bonus is None:
                        return bonus
                    score += bonus
        return score
    return _fn


def mismatchFilter ():
    '''
    Looks for mismatched tags (i.e., tags which match the first position, and are therefore equivalent,
    but with a different sub-tag).
    '''
    return __groupComparer(comparisonMode=TagComparison.MISMATCH, bonus=None, cumulative=False)
