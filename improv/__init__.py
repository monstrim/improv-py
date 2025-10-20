'''
A Python port of Bruno Dias's Improv library for JavaScript. 
Improv is a model-backed generative text grammar tool: Improv is similar to 
Tracery in that it can generate random, procedurally generated text 
recursively. Also like Tracery, Improv includes some basic templating 
functionality.

Unlike Tracery, however, Improv generators refer to *models* to build text. 
This allows for more sophisticated text generation by referencing an underlying 
world model.
'''

__version__ = '1.0.1'
__author__ = 'Pedro Monstrinho Araujo'


from improv.improv import Improv
from improv.model import Model