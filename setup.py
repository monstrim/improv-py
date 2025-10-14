import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from setuptools import setup
import improv

setup(
    name = 'improv-py',
    description = 'A port of Bruno Dias\'s Improv, a model-backed generative text grammar tool for javascript, to Python',
    license = 'MIT',
    author = improv.__author__,
    version = improv.__version__,    
    url = 'https://github.com/monstrim/improv-py',

    packages = ['improv'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)