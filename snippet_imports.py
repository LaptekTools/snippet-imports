"""Local, non-executing Python snippet import picker. Python 3.12+, stdlib only."""
import argparse
import ast
import builtins
import hashlib
import json
import sys
import symtable
import tokenize
from pathlib import Path

MAX_BYTES = 100_000
MAX_NODES = 20_000

class ReviewRequired(ValueError):
    pass

def first_line(node):
    return min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])])

def pick_imports(source, start, end):
    """Return metadata/code only. Never import, evaluate or run input source."""
    if len(source.encode('utf-8')) > MAX_BYTES:
        raise ReviewRequired('Source exceeds 100000-byte analysis limit.')
    lines = source.splitlines(keepends=True)
    if not 1 <= start <= end <= len(lines):
        raise ReviewRequired('Line range must be inclusive and within the source.')
    try:
        tree = ast.parse(source)
    except (SyntaxError, RecursionError) as exc:
        raise ReviewRequired('Source is not supported valid Python syntax.') from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_NODES:
        raise ReviewRequired('Source exceeds AST node limit.')
    selected = [n for n in tree.body if first_line(n) <= end and n.end_lineno >= start]
    if not selected or any(first_line(n) < start or n.end_lineno > end for n in selected):
        raise ReviewRequired('Select complete module-level statements, including decorators.')
    snippet = ''.join(lines[start-1:end])
    selected_tree = ast.parse(snippet)
    if any(isinstance(n, (ast.Import, ast.ImportFrom)) and any(a.name == '*' for a in n.names) for n in nodes):
        raise ReviewRequired('Wildcard imports need manual selection.')
    annotation_names = set()
    for n in ast.walk(selected_tree):
        if isinstance(n,ast.ClassDef):
            raise ReviewRequired('Class scopes need manual import review in this version.')
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'eval','exec','globals','locals','__import__'}:
            raise ReviewRequired('Dynamic namespace lookup needs manual review.')
        annotation = getattr(n, 'annotation', None)
        if annotation is None and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annotation = n.returns
        if annotation is not None and any(isinstance(x, ast.Constant) and isinstance(x.value,str) for x in ast.walk(annotation)):
            raise ReviewRequired('String annotations need manual import review.')
        if annotation is not None:
            annotation_names.update(x.id for x in ast.walk(annotation) if isinstance(x,ast.Name))
    try:
        table = symtable.symtable(snippet, '<selected snippet>', 'exec')
        full = symtable.symtable(source, '<source>', 'exec')
    except (SyntaxError, RecursionError) as exc:
        raise ReviewRequired('Selected statements do not form a supported compilation unit.') from exc
    selected_bindings = {s.get_name() for s in table.get_symbols() if s.is_assigned() or s.is_imported()}
    used = set()
    def globals_in(t):
        for symbol in t.get_symbols():
            if symbol.is_global() and symbol.is_referenced():
                used.add(symbol.get_name())
        for child in t.get_children():
            globals_in(child)
    globals_in(table)
    used.update(annotation_names)
    all_referenced_globals = used.copy()
    used -= selected_bindings
    if 'importlib' in used:
        raise ReviewRequired('Importlib use needs manual review.')
    top_imports = [n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
    mapping = {}
    for n in top_imports:
        if isinstance(n, ast.ImportFrom) and n.module == '__future__':
            continue
        for a in n.names:
            name = a.asname or (a.name.split('.')[0] if isinstance(n,ast.Import) else a.name)
            mapping.setdefault(name, []).append((n,a))
    conditional_names = set()
    for n in nodes:
        if isinstance(n,(ast.Import,ast.ImportFrom)) and n not in top_imports:
            for a in n.names:
                conditional_names.add(a.asname or (a.name.split('.')[0] if isinstance(n,ast.Import) else a.name))
    if conditional_names & used:
        raise ReviewRequired('Required import is conditional or nested; preserve its context manually.')
    global_writes = set()
    def assigned_globals(t):
        for symbol in t.get_symbols():
            if symbol.is_global() and symbol.is_assigned():
                global_writes.add(symbol.get_name())
        for child in t.get_children():
            assigned_globals(child)
    assigned_globals(full)
    ambiguous = all_referenced_globals & mapping.keys() & global_writes
    if ambiguous:
        raise ReviewRequired('Imported global may be rebound: '+', '.join(sorted(ambiguous)))
    import_names = used & mapping.keys()
    for name in import_names:
        if len(mapping[name]) != 1 or full.lookup(name).is_assigned():
            raise ReviewRequired('Imported name has multiple bindings or reassignment: '+name)
    imports = []
    for n in top_imports:
        # Future features affect parsing/annotation semantics even when not names.
        if isinstance(n,ast.ImportFrom) and n.module == '__future__':
            if not (start <= n.lineno <= end):
                imports.append(ast.unparse(n))
            continue
        aliases = [a for a in n.names if (a.asname or (a.name.split('.')[0] if isinstance(n,ast.Import) else a.name)) in import_names]
        if aliases:
            item = ast.Import(names=aliases) if isinstance(n,ast.Import) else ast.ImportFrom(module=n.module,names=aliases,level=n.level)
            imports.append(ast.unparse(item))
    shadowed_builtins = {s.get_name() for s in full.get_symbols() if s.is_assigned() or s.is_imported()}
    unresolved = sorted(used - import_names - (set(dir(builtins)) - shadowed_builtins))
    warnings = []
    if unresolved:
        warnings.append('External names are not bundled: '+', '.join(unresolved))
    if any(isinstance(n,ast.ImportFrom) and n.level and any(a.asname or a.name in import_names for a in n.names) for n in top_imports):
        warnings.append('Relative imports still require the original package context.')
    warnings.append('Import selection is static. Side-effect imports, runtime state, installed packages and standalone execution are not verified.')
    code = ('\n'.join(imports)+'\n\n' if imports else '') + snippet
    return dict(status='preview',source_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),range=[start,end],imports=imports,unresolved_names=unresolved,warnings=warnings,code=code)

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--lines',required=True,help='Inclusive complete module-level statement range, e.g. 5:8')
    parser.add_argument('--format',choices=['json','code'],default='json',help='Preview JSON by default; code prints to stdout. Neither writes files.')
    parser.add_argument('--stop-file',type=Path,default=Path(__file__).with_name('STOP'))
    args=parser.parse_args(argv)
    try:
        if args.stop_file.exists():
            raise ReviewRequired('Stopped: remove the STOP file to resume.')
        if args.source.stat().st_size > MAX_BYTES:
            raise ReviewRequired('Source exceeds 100000-byte analysis limit.')
        with tokenize.open(args.source) as f:
            source=f.read(MAX_BYTES+1)
        start,end=map(int,args.lines.split(':'))
        result=pick_imports(source,start,end)
        if args.stop_file.exists():
            raise ReviewRequired('Stopped before emitting output.')
        print(json.dumps(result,ensure_ascii=True,indent=2) if args.format=='json' else result['code'])
        # Metadata only; source content/paths/names are absent from the log.
        print(json.dumps(dict(event='preview',sha256=result['source_sha256'],range=result['range'],import_statement_count=len(result['imports']),warnings=len(result['warnings']))),file=sys.stderr)
        return 0
    except (ReviewRequired,OSError,UnicodeError,ValueError,SyntaxError,RecursionError) as exc:
        # No partial executable preview on unsupported input or a dependency failure.
        reason='Could not read source file; check existence and permissions.' if isinstance(exc,OSError) else str(exc)
        print(json.dumps(dict(status='manual_review',reason=reason)),file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
