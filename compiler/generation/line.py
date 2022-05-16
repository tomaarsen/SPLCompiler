from dataclasses import dataclass
from typing import Tuple

from compiler.generation.instruction import Instruction


@dataclass
class Line:
    label: str
    instruction: Tuple[str]
    comment: str

    def __init__(
        self, *instruction: Tuple[Instruction | str], label: str = "", comment: str = ""
    ) -> None:
        self.label = label
        self.instruction = instruction
        self.comment = comment.replace("\n", "")

    def __repr__(self) -> str:
        label = f"\n{self.label}:\t" if self.label else "\t"
        instruction = " ".join(str(instruction) for instruction in self.instruction)
        comment = f"\t\t\t; {self.comment}" if self.comment else ""
        return label + instruction + comment
