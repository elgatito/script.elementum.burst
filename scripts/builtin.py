#!/usr/bin/env python3
"""Writes the "builtin" part of every provider in burst/providers/providers.json.

Elementum has its own torrent search that reads this same file. It cannot run the Python expressions
of "parser", "login_object" and the like, so each provider carries them a second time under "builtin",
as plain JSON that Elementum evaluates (see providers/burst/selector.go in Elementum). Burst itself
ignores "builtin".

Run it after editing a provider: make builtin
A provider with an expression this script does not understand gets "builtin": {"unsupported": "..."}
and is not searched by Elementum.
"""
import ast
import collections
import json
import os

class Unsupported(Exception):
    pass

def lit(node):
    try:
        return ast.literal_eval(node)
    except Exception:
        raise Unsupported("not a literal: " + type(node).__name__)

def select(value):
    """('class', 'x') | ('class', ['a', 'b']) | [(..), (..)] -> [[key, [values]], ...]"""
    if value is None:
        return None
    if isinstance(value, tuple):
        value = [value]
    return [[k, v if isinstance(v, list) else [v]] for k, v in value]

def call_args(node, names):
    """Positional and keyword arguments of a call as a dict, by the parameter names of the ehp method."""
    if len(node.args) > len(names):
        raise Unsupported("too many arguments")
    args = dict(zip(names, (lit(a) for a in node.args)))
    for kw in node.keywords:
        if kw.arg not in names:
            raise Unsupported("unknown argument " + str(kw.arg))
        args[kw.arg] = lit(kw.value)
    return args

def name_of(func):
    """'item', 'find_all', 'item.find_all', 're.search' ... for a call's func, with the receiver node."""
    if isinstance(func, ast.Name):
        return func.id, None
    if isinstance(func, ast.Attribute):
        return func.attr, func.value
    raise Unsupported("call of " + type(func).__name__)

def is_root(node):
    """The row (item) or the page: the implicit receiver."""
    return node is None or (isinstance(node, ast.Name) and node.id in ("item", "dom"))

def nodes(node):
    """Expression giving elements: a chain of find_once/find_all -> list of steps."""
    if is_root(node):
        return []
    if isinstance(node, ast.Call):
        fn, recv = name_of(node.func)
        if fn == "find_once":
            a = call_args(node, ["tag", "select", "order"])
            return nodes(recv) + [clean({"tag": a.get("tag"), "select": select(a.get("select")), "nth": a.get("order", 1)})]
        if fn == "find_all":
            a = call_args(node, ["tag", "select", "every", "start"])
            return nodes(recv) + [clean({"tag": a.get("tag"), "select": select(a.get("select")), "all": True,
                                         "start": a.get("start", 1), "every": a.get("every", 1)})]
        if fn == "take_with_root":
            return nodes(recv) + [{"parent_of": select(lit(node.args[0]))}]
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Call):
        steps = nodes(node.value)
        index = lit(node.slice)
        if steps and isinstance(index, int):
            last = dict(steps[-1])
            if last.pop("all", None):
                last.pop("start", None), last.pop("every", None)
                last["nth"] = index + 1  # nth 0 is the last element, as ehp's list[order - 1]
                return steps[:-1] + [last]
            if "parent_of" in last and index == 0:
                return steps
    raise Unsupported("elements: " + type(node).__name__)

def clean(d):
    return dict((k, v) for k, v in d.items() if v is not None and not (k in ("start", "every", "nth") and v == 1))

def text(node):
    """Expression giving a string -> spec."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int)):
        return str(node.value)
    if isinstance(node, ast.Name) and node.id == "key":
        return {"op": "key"}
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant):
        return {"op": "format", "format": node.left.value, "arg": text(node.right)}
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        parts = []
        for side in (node.left, node.right):
            t = text(side)
            parts.extend(t["args"] if isinstance(t, dict) and t.get("op") == "concat" else [t])
        return {"op": "concat", "args": parts}
    if isinstance(node, ast.IfExp):
        return {"op": "if", "test": text(node.test), "then": text(node.body), "else": text(node.orelse)}
    if isinstance(node, ast.Subscript):
        # .attr['href'] on elements
        if isinstance(node.value, ast.Attribute) and node.value.attr == "attr":
            return {"in": nodes(node.value.value), "attr": lit(node.slice), "raw": True}
        # x.split(sep, n)[i]
        if isinstance(node.value, ast.Call) and name_of(node.value.func)[0] == "split":
            call = node.value
            a = [lit(x) for x in call.args]
            return {"op": "split", "arg": text(call.func.value), "sep": a[0], "max": a[1] if len(a) > 1 else -1, "index": lit(node.slice)}
        if isinstance(node.slice, ast.Slice):
            s = node.slice
            return clean({"op": "slice", "arg": text(node.value), "from": lit(s.lower) if s.lower else None, "to": lit(s.upper) if s.upper else None})
        raise Unsupported("subscript")
    if isinstance(node, ast.Call):
        # find_once(...)(tag=..., ...): an element called like item
        inside = nodes(node.func) if isinstance(node.func, ast.Call) else None
        fn, recv = ("item", None) if inside is not None else name_of(node.func)
        if fn == "item" and recv is None:
            a = call_args(node, ["tag", "order", "select", "attribute", "divider"])
            spec = clean({"in": inside, "tag": a.get("tag"), "select": select(a.get("select")), "nth": a.get("order", 1)})
            if a.get("attribute", "text") != "text":
                spec["attr"] = a["attribute"]
            if a.get("divider", ("", 1))[0] != "":
                spec["divider"] = list(a["divider"])
            return spec
        if fn == "text" and not node.args:
            return {"in": nodes(recv), "raw": True}
        if fn == "group" and isinstance(recv, ast.Call) and name_of(recv.func)[0] == "search":
            return {"op": "regex", "pattern": lit(recv.args[0]), "arg": text(recv.args[1]), "group": lit(node.args[0])}
        if fn == "sub" and isinstance(recv, ast.Name) and recv.id == "re":
            return {"op": "resub", "pattern": lit(node.args[0]), "repl": lit(node.args[1]), "arg": text(node.args[2])}
        if fn == "unquote":
            return {"op": "unquote", "arg": text(node.args[0])}
        if fn == "replace":
            return {"op": "replace", "arg": text(recv), "old": lit(node.args[0]), "new": text(node.args[1])}
        if fn == "upper":
            return {"op": "upper", "arg": text(recv)}
    raise Unsupported(type(node).__name__)

def builtin(provider):
    """The "builtin" part of a provider: what Elementum's built-in search reads in place of the Python
    expressions of the same name."""
    out = {}
    parser = {}
    for field, expression in (provider.get("parser") or {}).items():
        if not expression:
            continue
        try:
            tree = ast.parse(expression, mode="eval").body
            parser[field] = nodes(tree) if field == "row" else text(tree)
        except SyntaxError:
            out["unsupported"] = "parser.%s: not valid Python" % field
        except (Unsupported, ValueError, IndexError, TypeError) as e:
            # kept free of anything that changes between Python versions, CI compares the output
            out["unsupported"] = "parser.%s: %s" % (field, str(e) if isinstance(e, Unsupported) else type(e).__name__)
    if parser:
        out["parser"] = parser
    for field in ("post_data", "headers", "login_object", "login_headers"):
        if provider.get(field):
            try:
                out[field] = form(provider[field])
            except Exception as e:
                out["unsupported"] = "%s: %s" % (field, str(e) if isinstance(e, Unsupported) else type(e).__name__)
    return out

def form(expression):
    """A dict literal of a request -> {name: text}. The names USERNAME, PASSWORD and CSRF_TOKEN stay as
    those words, which Elementum replaces; definition['key'] becomes {key}."""
    tree = ast.parse(expression.strip(), mode="eval").body
    if not isinstance(tree, ast.Dict):
        raise Unsupported("not a dict")
    result = {}
    for k, v in zip(tree.keys, tree.values):
        if isinstance(v, ast.Name):
            value = v.id
        elif isinstance(v, ast.Subscript) and isinstance(v.value, ast.Name) and v.value.id == "definition":
            value = "{%s}" % lit(v.slice)
        else:
            value = str(lit(v))
        result[str(lit(k))] = value
    return result

def main():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "burst", "providers", "providers.json")
    with open(path, encoding="utf-8") as f:
        providers = json.load(f, object_pairs_hook=collections.OrderedDict)
    bad = {}
    for name, provider in providers.items():
        provider.pop("builtin", None)
        part = builtin(provider)
        if part:
            # sorted, so a rerun without changes rewrites nothing
            provider["builtin"] = json.loads(json.dumps(part, sort_keys=True), object_pairs_hook=collections.OrderedDict)
        if "unsupported" in part:
            bad[name] = part["unsupported"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(providers, f, ensure_ascii=False, indent=4)
        f.write("\n")
    print("%d providers, %d not converted" % (len(providers), len(bad)))
    for name, why in sorted(bad.items()):
        print("  %s: %s" % (name, why))


if __name__ == "__main__":
    main()
