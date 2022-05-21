from prolog_test_compiler.scanner import Scanner

program = """
a = 1 * 3 + 9;
b = 7 * 8 + 11;
"""

scanner = Scanner(program)
tokens = scanner.scan()

print(tokens)
