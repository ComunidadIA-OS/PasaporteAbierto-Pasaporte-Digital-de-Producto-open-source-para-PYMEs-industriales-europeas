"""Evaluador seguro de condiciones `when` de plugins YAML.

Las expresiones `when` del plugin usan una sintaxis tipo Python:
  - `battery_category in [industrial, ev]`
  - `rated_capacity_ah * voltage_nominal_v / 1000 > 2`

Este módulo las evalúa sin `eval()` usando parsing manual con `ast`.
"""

from __future__ import annotations

import ast
import operator
from typing import Any

_OPERATORS = {
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def evaluate_when(condition: str | None, bom: dict[str, Any]) -> bool:
    """Evalúa una condición `when` del plugin contra el BOM.

    Devuelve True si la condición se cumple o si `condition` es None/vacío
    (documento siempre requerido).
    """
    if not condition:
        return True

    try:
        tree = ast.parse(condition, mode="eval")
        return bool(_eval_node(tree.body, bom))
    except Exception:
        # Si no se puede parsear, el documento se requiere por precaución
        return True


def _eval_node(node: ast.expr, bom: dict[str, Any]) -> Any:
    """Evalúa recursivamente un nodo AST con acceso al BOM."""
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, bom)
        for op_node, comparator in zip(node.ops, node.comparators, strict=True):
            right = _eval_node(comparator, bom)
            if isinstance(op_node, ast.In):
                return left in right
            if isinstance(op_node, ast.NotIn):
                return left not in right
            op_func = _OPERATORS.get(type(op_node))
            if op_func is None:
                raise ValueError(f"Operador no soportado: {type(op_node).__name__}")
            if not op_func(left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, bom)
        right = _eval_node(node.right, bom)
        op_func = _OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"Operador no soportado: {type(node.op).__name__}")
        return op_func(left, right)

    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_eval_node(v, bom) for v in node.values)
        if isinstance(node.op, ast.Or):
            return any(_eval_node(v, bom) for v in node.values)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval_node(node.operand, bom)

    if isinstance(node, ast.Name):
        # Bareword inside a list like `[industrial, ev]` — treat as string
        # Also handles BOM field lookups
        if node.id == "null" or node.id == "None":
            return None
        return bom.get(node.id, node.id)

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.List):
        return [_eval_node(e, bom) for e in node.elts]

    if isinstance(node, ast.Subscript):
        value = _eval_node(node.value, bom)
        idx = _eval_node(node.slice, bom)
        return value[idx]

    raise ValueError(f"Nodo AST no soportado: {type(node).__name__}")
