# Improv

A Python port of [Bruno Dias's Improv](https://github.com/sequitur/improv) library for JavaScript. Improv is a model-backed generative text grammar tool: Improv is similar to [Tracery](https://tracery.io/) in that it can generate random, procedurally generated text recursively. Also like Tracery, Improv includes some basic templating functionality.

Unlike Tracery, however, Improv generators refer to *models* to build text. This allows for more sophisticated text generation by referencing an underlying world model.

## Quick Example

```python
from improv import Model, Improv, filters

snippets = {
    'animal': {
        'bind': False,
        'groups': [
            {
                'tags': 'class mammal',
                'phrases': ['dog', 'cat']
            },
            {
                'tags': 'class bird',
                'phrases': ['parrot']
            }
        ]
    },
    'root': {
        'groups': [
            {
                'repeat': True,
                'phrases': [
                    '[name]: I have [an :animal] who is [#2-7] years old.'
                ]
            }
        ]
    }
}

improv = Improv(
    snippets, 
    filters = [filters.mismatchFilter()]
)

alice = Model(name= 'Alice') 
bob = Model(name= 'Bob', tags= 'class mammal')
carol = Model(name= 'Carol', tags= 'class bird')

print(improv.gen('root', alice))
print(improv.gen('root', bob))
print(improv.gen('root', carol))

'''
Should produce something like:
  Alice: I have a cat who is 2 years old.
  Bob: I have a dog who is 3 years old.
  Carol: I have a parrot who is 5 years old.
'''

```

## Documentation

The original, JavaScript, lib has its documentation at [Read the Docs](http://improv.readthedocs.org/en/latest/). 
The port attempts to stick to that. It uses the same calls:
- `gen (snippetName, model)`
- `getSubModel (model, subModelName)`
- `clearHistory ()`
- `clearTagHistory ()`
- `phraseAudit ()`

Snippets follow the original syntax. JavaScript has a particular way in which everything is automatically an object,
so I added a Model class with a constructor that adds any kwargs as attributes of the object. I changed the names of 
a few filters (they all end in Filter or Bonus, so `dryness` => `repeatFilter` and `unmentioned` => `unmentionedBonus`) 
and added an optional per-group `repeat` flag for use with the repeatFilter. Everything else should just work as per the original.

## Caveats and Known Issues

Improv does absolutely no validation or security checking of anything, so for the love of God don't pass user-submitted data into it.

## License

MIT © [Pedro Monstrinho Araujo](https://github.com/monstrim)
