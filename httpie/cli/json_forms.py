"""
Routines for JSON forms syntax, used to support nested JSON request items.

Highly inspired from the great jarg project <https://github.com/jdp/jarg/blob/master/jarg/jsonform.py>.
"""
import json
from typing import Any, Dict, Union


def parse_path(path: str) -> str:
    """
    Parse a string as a JSON path.

    An implementation of "steps to parse a JSON encoding path".
    <https://www.w3.org/TR/html-json-forms/#dfn-steps-to-parse-a-json-encoding-path>

    """
    original = path
    failure = [(original, {'last': True, 'type': object})]
    steps = []
    try:
        first_key = path[:path.index('[')]
        if not first_key:
            return original
        steps.append((first_key, {'type': 'object'}))
        path = path[path.index('['):]
    except ValueError:
        return failure
    while path:
        if path.startswith('[]'):
            steps[-1][1]['append'] = True
            path = path[2:]
            if path:
                return failure
        elif path[0] == '[':
            path = path[1:]
            try:
                key = path[:path.index(']')]
                path = path[path.index(']') + 1:]
            except ValueError:
                return failure
            try:
                steps.append((int(key), {'type': 'array'}))
            except ValueError:
                steps.append((key, {'type': 'object'}))
        else:
            return failure
    for i in range(len(steps) - 1):
        steps[i][1]['type'] = steps[i + 1][1]['type']
    steps[-1][1]['last'] = True
    return steps


def set_value(context, step, current_value, entry_value):
    """Apply a JSON value to a context object.

    An implementation of "steps to set a JSON encoding value".
    <https://www.w3.org/TR/html-json-forms/#dfn-steps-to-set-a-json-encoding-value>

    """
    key, flags = step
    if flags.get('last', False):
        if current_value is None:
            if flags.get('append', False):
                context[key] = [entry_value]
            else:
                if isinstance(context, list) and len(context) <= key:
                    context.extend([None] * (key - len(context) + 1))
                context[key] = entry_value
        elif isinstance(current_value, list):
            context[key].append(entry_value)
        elif isinstance(current_value, dict):
            set_value(
                current_value, ('', {'last': True}),
                current_value.get('', None), entry_value)
        else:
            context[key] = [current_value, entry_value]
        return context
    else:
        if current_value is None:
            if flags.get('type') == 'array':
                context[key] = []
            else:
                if isinstance(context, list) and len(context) <= key:
                    context.extend([None] * (key - len(context) + 1))
                context[key] = {}
            return context[key]
        elif isinstance(current_value, dict):
            return context[key]
        elif isinstance(current_value, list):
            if flags.get('type') == 'array':
                return current_value
            else:
                obj = {}
                for i, item in enumerate(current_value):
                    if item is not None:
                        obj[i] = item
                else:
                    context[key] = obj
                return obj
        else:
            obj = {'': current_value}
            context[key] = obj
            return obj


def encode(pairs: Dict[str, str]) -> Dict[str, Any]:
    """The application/json form encoding algorithm.

    <https://www.w3.org/TR/html-json-forms/#dfn-application-json-encoding-algorithm>

    """
    result = {}
    for key, value in pairs:
        steps = parse_path(key)
        context = result
        for step in steps:
            try:
                current_value = context.get(step[0], None)
            except AttributeError:
                try:
                    current_value = context[step[0]]
                except IndexError:
                    current_value = None
            context = set_value(context, step, current_value, value)
    return result


def to_python(value: str) -> Union[None, str, int, float]:
    """Try to convert the JSON-like `value` to a known specialized Python object.

    """
    try:
        return json.loads(value)
    except ValueError:
        pass
    return value
