from dataclasses import dataclass
from pprint import pprint

from compiler.token import Token
from compiler.tree.tree import Node


class NodeVisitor:
    """
    For visiting nodes in our AST
    """

    def visit(self, node: Node | Token, *args, **kwargs):
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.visit_children)
        return visitor(node, *args, **kwargs)

    def visit_children(self, node: Node | Token, *args, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        if isinstance(node, Token):
            return
        for field, value in node.iter_fields():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, (Node, Token)):
                        self.visit(item, *args, **kwargs)
            elif isinstance(value, (Node, Token)):
                self.visit(value, *args, **kwargs)


class NodeTransformer(NodeVisitor):
    """
    For transforming our AST
    """

    def visit_children(self, node: Node | Token, *args, **kwargs):
        if isinstance(node, Token):
            return node

        for field, old_value in node.iter_fields():
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, (Node, Token)):
                        value = self.visit(value, *args, **kwargs)
                        if value is None:
                            continue
                        elif not isinstance(value, (Node, Token)):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, (Node, Token)):
                new_node = self.visit(old_value, *args, **kwargs)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node


class YieldVisitor(NodeVisitor):
    """
    For yielding values from nodes in our AST
    """

    def visit(self, node: Node | Token, *args, **kwargs):
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.visit_children)
        yield from visitor(node, *args, **kwargs)

    def visit_children(self, node: Node | Token, *args, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        if isinstance(node, Token):
            return
        for field, value in node.iter_fields():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, (Node, Token)):
                        yield from self.visit(item, *args, **kwargs)

            elif isinstance(value, (Node, Token)):
                yield from self.visit(value, *args, **kwargs)


@dataclass
class Boolean:
    """
    An instanced wrapper of a `bool` that can be passed along a function,
    modified deeper in the call stack, and then those changes can be read
    up higher.

    >>> def func(bl: Boolean):
    >>>     bl.set(False)
    >>> bl = Boolean(True)
    >>> bl
    Boolean(boolean=True)
    >>> func(bl)
    >>> bl
    Boolean(boolean=False)
    """

    boolean: bool

    def set(self, boolean: bool) -> None:
        self.boolean = boolean

    def __bool__(self) -> bool:
        return self.boolean
