from typing import List

from autodx.viz.support import *

YELLOW = "#fefecd" # "#fbfbd0" # "#FBFEB0"
BLUE = "#D9E6F5"
GREEN = "#cfe2d4"

class Expr:
    def __init__(self, x : numbers.Number = 0):
        self.x = x
        self.vi = -1
        self.varname = None

    def __add__(self, other):
        if isinstance(other, numbers.Number):
            other = Const(other)
        return Add(self,other)

    def __radd__(self, other):
        return Add(Const(other),self) # other comes in as left operand so we flip order

    def __sub__(self, other):
        if isinstance(other, numbers.Number):
            other = Const(other)
        return Sub(self,other)

    def __rsub__(self, other):
        return Sub(Const(other),self) # other comes in as left operand so we flip order

    def __mul__(self, other: 'Expr') -> 'Expr':  # yuck. must put 'Variable' type in string
        if isinstance(other, numbers.Number):
            other = Const(other)
        return Mul(self,other)

    def __rmul__(self, other):
        "Allows 5 * Variable(3) to invoke overloaded * operator"
        return Mul(Const(other),self) # other comes in as left operand so we flip order

    def __truediv__(self, other):
        if isinstance(other, numbers.Number):
            other = Const(other)
        return Div(self,other)

    def __rtruediv__(self, other):
        return Div(Const(other),self) # other comes in as left operand so we flip order

    def value(self) -> numbers.Number:
        return self.x

    def gradient(self, X):
        return [self.dvdx(x) for x in X]

    def children(self):
        return []

    def __repr__(self):
        return str(self)

class Var(Expr):
    def __init__(self, x : numbers.Number, varname : str = None):
        self.x = x
        self.vi = -1
        self.varname = varname

    def dvdx(self, wrt : 'Expr') -> numbers.Number:
        return 1 if self==wrt else 0

    def __str__(self):
        if isinstance(self.x, int):
            return f'Var({self.x})'
        return f'Var({self.x:.4f})'


class Const(Expr):
    def __init__(self, v : numbers.Number):
        self.x = v
        self.vi = -1
        self.varname = None

    def dvdx(self, wrt : 'Expr') -> numbers.Number:
        return 0

    def __str__(self):
        if isinstance(self.x, int):
            return f'{self.x}'
        else:
            return f'{round(self.x)}'


class BinaryOp(Expr):
    def __init__(self, left : Expr, op: str, right : Expr):
        super().__init__()
        self.left = left
        self.op = op
        self.right = right

    def children(self):
        return [self.left, self.right]

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"


class UnaryOp(Expr):
    def __init__(self, op : str, opnd : Expr):
        super().__init__()
        self.opnd = opnd
        self.op = op

    def children(self):
        return [self.opnd]

    def __str__(self):
        return f"{self.op}({self.opnd})"



class Add(BinaryOp):
    def __init__(self, left, right):
        super().__init__(left, '+', right)

    def value(self):
        return self.left.value() + self.right.value()

    def dvdx(self, wrt : Expr) -> numbers.Number:
        return self.left.dvdx(wrt) + self.right.dvdx(wrt)


class Sub(BinaryOp):
    def __init__(self, left, right):
        super().__init__(left, '-', right)

    def value(self):
        return self.left.value() - self.right.value()

    def dvdx(self, wrt : Expr) -> numbers.Number:
        return self.left.dvdx(wrt) - self.right.dvdx(wrt)


class Mul(BinaryOp):
    def __init__(self, left, right):
        super().__init__(left, '*', right)

    def value(self):
        return self.left.value() * self.right.value()

    def dvdx(self, wrt : Expr) -> numbers.Number:
        return self.left.value() * self.right.dvdx(wrt) + \
               self.right.value() * self.left.dvdx(wrt)


class Div(BinaryOp):
    def __init__(self, left, right):
        super().__init__(left, '/', right)

    def value(self):
        return self.left.value() / self.right.value()

    def dvdx(self, wrt : Expr) -> numbers.Number:
        return (self.left.dvdx(wrt) * self.right.value() - self.left.value() * self.right.dvdx(wrt)) / \
               self.right.value()**2


class Sin(UnaryOp):
    def __init__(self, opnd):
        super().__init__('sin', opnd)

    def value(self):
        return np.sin(self.opnd.value())

    def dvdx(self, wrt : Expr) -> numbers.Number:
        return np.cos(self.opnd.value()) * self.opnd.dvdx(wrt)


class Ln(UnaryOp):
    def __init__(self, opnd):
        super().__init__('ln', opnd)

    def value(self):
        return np.log(self.opnd.value())

    def dvdx(self, wrt : Expr) -> numbers.Number:
        return (1 / self.opnd.value()) * self.opnd.dvdx(wrt)


def sin(x:Expr) -> Sin:
    if isinstance(x, numbers.Number):
        return Sin(Const(x))
    return Sin(x)


def ln(x:Expr) -> Ln:
    if isinstance(x, numbers.Number):
        return Ln(Const(x))
    return Ln(x)


def leaves(t : Expr) -> List[Expr]:
    """Return preorder list of nodes from ast t"""
    the_leaves = []
    work = [t]
    while len(work)>0:
        node = work.pop(0)
        if len(node.children())==0:
            if node not in the_leaves:
                the_leaves.append(node)
        else:
            work += node.children()
    return the_leaves


def set_var_indices(t : Expr, first_index : int = 0) -> None:
    the_leaves = leaves(t)
    inputs = [n for n in the_leaves if isinstance(n, Var)]
    i = first_index
    for leaf in inputs:
        leaf.vi = i
        if leaf.varname is None:
            leaf.varname = sub("x", i)
        i += 1

    set_var_indices_(t,i)


def set_var_indices_(t : Expr, vi : int) -> int:
    if t.vi >= 0:
        return vi
    if isinstance(t, Var):
        t.vi = vi
        return t.vi + 1
    elif isinstance(t, Const):
        t.vi = vi
        return t.vi + 1
    elif isinstance(t, BinaryOp):
        vi = set_var_indices_(t.left,vi)
        vi = set_var_indices_(t.right,vi)
        t.vi = vi
        return t.vi + 1
    elif isinstance(t, UnaryOp):
        t.vi = set_var_indices_(t.opnd,vi)
        return t.vi + 1
    return vi