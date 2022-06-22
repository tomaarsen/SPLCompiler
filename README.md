# SPLCompiler
A compiler for a Simple Programming Language, written in Python, defined through [this Context Free Grammar](https://github.com/tomaarsen/SPLCompiler/blob/main/compiler/parser/grammar.txt).

## Usage
Use Python 3.10 to compile SPL programs to [SSM](https://gitlab.science.ru.nl/compilerconstruction/ssm/-/tree/master "SSM GitLab repository") and execute them. Note that this requires this SSM repository to be cloned into a separate `ssm` folder adjacent to the `compiler` directory.
```
python compile.py
```
A .spl file can be loaded either by supplying a file reference to the ``open_file`` function, or by manually defining a program using a raw string in ``compile.py``.

## Tests
Run ``pytest`` to execute all of the available tests.

## Authors:
* Tom Aarsen
* Mathieu Bangma
