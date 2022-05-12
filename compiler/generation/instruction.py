from enum import Enum, auto


class Instruction(Enum):
    LDC = auto()  # Load Constant
    LDS = auto()  # Load from Stack
    LDMS = auto()  # Load Multiple from Stack
    STS = auto()  # Store into Stack
    STMS = auto()  # Store Multiple into Stack
    LDSA = auto()  # Load Stack Address
    LDL = auto()  # Load Local
    LDML = auto()  # Load Multiple Local
    STL = auto()  # Store Local
    STML = auto()  # Store Multiple Local
    LDLA = auto()  # Load Local Address
    LDA = auto()  # Load via Address
    LDMA = auto()  # Load Multiple via Address
    LDAA = auto()  # Load Address of Address
    STA = auto()  # Store via Address
    STMA = auto()  # Store Multiple via Address
    LDR = auto()  # Load Register
    LDRR = auto()  # Load Register from Register
    STR = auto()  # Store Register
    SWP = auto()  # Swap values
    SWPR = auto()  # Swap Register
    SWPRR = auto()  # Swap 2 Registers
    AJS = auto()  # Adjust Stack

    ADD = auto()  # Addition
    MUL = auto()  # Multiplication
    SUB = auto()  # Subtraction
    DIV = auto()  # Division
    MOD = auto()  # Modulo
    AND = auto()  # Bitwise AND
    OR = auto()  # Bitwise OR
    XOR = auto()  # Bitwise XOR
    EQ = auto()  # Equality
    NE = auto()  # Non-equality
    LT = auto()  # Less than
    LE = auto()  # Less or equal
    GT = auto()  # Greater than
    GE = auto()  # Greater or equal
    NEG = auto()  # Negation
    NOT = auto()  # Bitwise complement

    BSR = auto()  # Branch to Subroutine
    BRA = auto()  # Branch Always
    BRF = auto()  # Branch on False
    BRT = auto()  # Branch on True
    JSR = auto()  # Jump to Subroutine
    RET = auto()  # Return from Subroutine

    LINK = auto()  # Reserve memory for locals
    UNLINK = auto()  # Free memory for locals
    NOP = auto()  # No operation
    HALT = auto()  # Halt execution
    TRAP = auto()  # Trap to environment function, involves a systemcall:
    """
     0: Pop the topmost element from the stack and print it as an integer.
     1: Pop the topmost element from the stack and print it as a unicode character.
    10: Ask the user for an integer input and push it on the stack.
    11: Ask the user for a unicode character input and push it on the stack.
    12: Ask the user for a sequence of unicode characters input and push the characters on the stack terminated by a null-character.
    20: Pop a null-terminated file name from the stack, open the file for reading and push a file pointer on the stack.
    21: Pop a null-terminated file name from the stack, open the file for writing and push a file pointer on the stack.
    22: Pop a file pointer from the stack, read a character from the file pointed to by the file pointer and push the character on the stack.
    23: Pop a character and a file pointer from the stack, write the character to the file pointed to by the file pointer.
    24: Pop a file pointer from the stack and close the corresponding file.
    """
    ANNOTE = auto()  # Annotate, color used in the GUI

    LDH = auto()  # Load from Heap
    LDMH = auto()  # Load Multiple from Heap
    STH = auto()  # Store into Heap
    STMH = auto()  # Store Multiple into Heap

    def __str__(self) -> str:
        return self.name.lower()
