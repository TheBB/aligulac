from django.db.models import Q
from django.db.models.expressions import F, ExpressionNode
import re

# {{{
_swap_regex = re.compile(r"^(sc|pl|rc)(a|b)")
def swap_q_object(q):
    qs = Q(*[_swap_q_child(c) for c in q.children])
    qs.connector = q.connector
    qs.negated = q.negated
    return qs

def _swap_q_child(child):
    if isinstance(child, Q):
        return swap_q_object(child)
    if isinstance(child, tuple):
        k, v = child
        if isinstance(v, F):
            return _swap(k), swap_f_object(v)
        return _swap(k), v

def swap_f_object(f):
    if isinstance(f, F):
        fs = F(_swap(f.name))
    elif isinstance(f, ExpressionNode):
        fs = ExpressionNode()
    fs.children = [swap_f_object(c) for c in f.children]
    fs.connector = f.connector
    fs.negated = f.negated
    return fs

def _repl(match):
    return match.group(1) + ("a" if match.group(2) == "b" else "b")

def _swap(key):
    return _swap_regex.sub(_repl, key)

# }}}
