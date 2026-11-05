class ASTNode:
    pass


class EmptyNode(ASTNode):
    """Matches the empty string (e.g. the right side of `a|`)."""

    def __repr__(self):
        return "Empty()"


class CharNode(ASTNode):
    def __init__(self, value):
        self.value = value  # CharSet

    def __repr__(self):
        return f"Char({self.value.label()})"


class ConcatNode(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Concat({self.left}, {self.right})"


class OrNode(ASTNode):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Or({self.left}, {self.right})"


class StarNode(ASTNode):
    def __init__(self, child):
        self.child = child

    def __repr__(self):
        return f"Star({self.child})"


class PlusNode(ASTNode):
    def __init__(self, child):
        self.child = child

    def __repr__(self):
        return f"Plus({self.child})"


class QuestionNode(ASTNode):
    def __init__(self, child):
        self.child = child

    def __repr__(self):
        return f"Question({self.child})"
