# SPLCompiler
Our compiler for SPL, written in Python.

## Usage
Use Python 3.10 to compile SPL programs to [SSM](https://gitlab.science.ru.nl/compilerconstruction/ssm/-/tree/master "SSM GitLab repository").
```
python compile.py
```
A .spl file can be loaded either by supplying a file reference to the ``open_file`` function, or by manually defining a program using a raw string in ``compile.py``.

## Tests
Run ``pytest`` to run all the available tests.

## Authors:
* Tom Aarsen
* Mathieu Bangma