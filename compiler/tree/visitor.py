from pprint import pprint

from compiler.token import Token
from compiler.tree.tree import Node


class NodeVisitor:
    """
    For visiting nodes in our AST
    """

    def visit(self, node: Node | Token, **kwargs):
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node, **kwargs)

    def generic_visit(self, node: Node | Token, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        if isinstance(node, Token):
            return
        for field, value in node.iter_fields():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, (Node, Token)):
                        self.visit(item, **kwargs)
            elif isinstance(value, (Node, Token)):
                self.visit(value, **kwargs)


class NodeTransformer(NodeVisitor):
    """
    For transforming our AST
    """

    def generic_visit(self, node: Node | Token, **kwargs):
        if isinstance(node, Token):
            return node

        for field, old_value in node.iter_fields():
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    if isinstance(value, (Node, Token)):
                        value = self.visit(value, **kwargs)
                        if value is None:
                            continue
                        elif not isinstance(value, (Node, Token)):
                            new_values.extend(value)
                            continue
                    new_values.append(value)
                old_value[:] = new_values
            elif isinstance(old_value, (Node, Token)):
                new_node = self.visit(old_value, **kwargs)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node


class YieldVisitor(NodeVisitor):
    """
    For yielding values from nodes in our AST
    """

    def visit(self, node: Node | Token, **kwargs):
        """Visit a node."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        yield from visitor(node, **kwargs)

    def generic_visit(self, node: Node | Token, **kwargs):
        """Called if no explicit visitor function exists for a node."""
        if isinstance(node, Token):
            return
        for field, value in node.iter_fields():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, (Node, Token)):
                        yield from self.visit(item, **kwargs)

            elif isinstance(value, (Node, Token)):
                yield from self.visit(value, **kwargs)
