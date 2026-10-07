# Snippet Imports

A free local Python utility for documentation authors working outside an IDE. Select a complete function or statement; preview the selected code with its referenced explicit module imports. The source is parsed, never executed. Python3.12+, standard library only, no network or account.

```sh
python snippet_imports.py example.py --lines 7:9
python snippet_imports.py example.py --lines 7:9 --format code
python test_snippet_imports.py
```

The fictional example returns:

```python
import json
from pathlib import Path
from statistics import mean

def describe(path):
    rows = json.loads(Path(path).read_text())
    return mean(rows)
```

It leaves out the unused median/time imports. JSON preview is the default dry run and includes unresolved names and limitations. Both formats print to stdout; metadata logs go to stderr. The program does not alter source, use the clipboard or create a background process. Stop with Ctrl+C or a file named STOP beside the script. Correct the input and rerun after a failed preview; duplicates are deterministic.

## Scope

Select complete module-level statements, including decorators. Tested cases include aliases, multiline imports, nested functions, local shadowing, comprehensions and static annotations. Wildcards, required conditional imports, rebound globals, dynamic namespace lookup, string annotations, classes and incomplete selections require manual review. Relative imports still need their package context. This does not resolve import side effects, installed packages or runtime state, and does not guarantee a runnable standalone program. Analysis is limited to100000UTF-8bytes and20000ASTnodes.

Thirty-eight fictional checks passed on Python3.12.14. A37902-byte/1000-function input took about0.105seconds with10.31MiB parser peak on the development machine. An initial version failed three additional rebinding/context cases; those were fixed before this release. These are parser measurements, not measured time saved by actual authors.

## Existing alternatives

[BetterPy](https://plugins.jetbrains.com/plugin/29896-betterpy) advertises selected-code import copying inside JetBrains IDEs and was free during its extended beta when checked7October2026. See [PY-62801](https://youtrack.jetbrains.com/issue/PY-62801/Copy-with-imports) and [IJPL-246014](https://youtrack.jetbrains.com/issue/IJPL-246014). This CLI is a limited outside-IDE alternative; it is not advertised as a missing paid PyCharm feature. Use the IDE solution if it already fits your workflow.

Feedback is useful when it describes a repeat documentation task, the manual baseline, correct or missing imports, and time spent. Use fictional or redacted examples in public issues; do not upload private source. Downloads and stars are not evidence of repeated usefulness. MIT license; experimental utility with no sales or payment link.
