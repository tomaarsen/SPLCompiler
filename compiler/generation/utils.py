from compiler.tree.tree import ForNode, Node
from compiler.tree.visitor import NodeVisitor


class ForCounterVisitor(NodeVisitor):
    def __init__(self) -> None:
        super().__init__()
        self._current_count = 0
        self.max = 0

    @property
    def current_count(self):
        return self._current_count

    @current_count.setter
    def current_count(self, value):
        """Track the increments/decrements in self.max"""
        self._current_count = value
        self.max = max(self.max, self.current_count)

    def count(self, node: Node):
        """Count the number of nested ForNode nodes."""
        self.visit(node)
        return self.max

    def visit_ForNode(self, node: ForNode, *args, **kwargs):
        """Increment, recurse, decrement"""
        self.current_count += 1
        self.visit_children(node)
        self.current_count -= 1
