# Copy a Python function with the imports it actually references

Copying a function into documentation often leaves you hunting for its imports. Copying every import from the original file adds unrelated dependencies. This walkthrough shows a narrow middle option: a local static preview of a complete function and its explicit module imports.

The example is fictional. These are verified parser outputs, not a claim of measured time saved by real users.

## 1. Try the included file

Download the repository using **Code → Download ZIP** and extract it, or clone it:

```sh
git clone https://github.com/LaptekTools/snippet-imports.git
cd snippet-imports
```

Use Python 3.12 or later. There are no Python packages to install. The included `example.py` contains:

```python
# Fictional input. The exporter never runs this file.
import json
from pathlib import Path
from statistics import mean, median
import time

def describe(path):
    rows = json.loads(Path(path).read_text())
    return mean(rows)

def unused():
    return median([1, 2, 3]), time.time()
```

Select the whole `describe` function, lines 7 through 9:

```sh
python snippet_imports.py example.py --lines 7:9
```

The default JSON preview reports `status: "preview"`, the selected range, three import statements, no unresolved names, and a warning about the limits of static analysis. It also includes the resulting code. It does not execute `example.py`, open the data file mentioned inside the function, or write a new source file.

For only the code on standard output:

```sh
python snippet_imports.py example.py --lines 7:9 --format code
```

Result:

```python
import json
from pathlib import Path
from statistics import mean

def describe(path):
    rows = json.loads(Path(path).read_text())
    return mean(rows)
```

`median` and `time` belong to the unused function and are omitted. Metadata is printed separately to standard error, so a terminal still shows a short log alongside the code. Review the JSON warnings before using the code output elsewhere.

## 2. Select statements, not arbitrary text

This command selects only the body of the function:

```sh
python snippet_imports.py example.py --lines 8:9
```

It exits with code **2**, reports `manual_review` on standard error, and emits no code on standard output. The selection must contain complete module-level statements. Include decorators when selecting a decorated function.

This is useful feedback: copying indented body lines cannot preserve the function's original context automatically. It is not a reason to force the preview through.

## 3. An import preview is not a standalone program

Create a separate fictional file named `external_example.py` with exactly these three lines:

```python
from pathlib import Path
def load(path):
    return normalize(Path(path).read_text())
```

Then preview its function:

```sh
python snippet_imports.py external_example.py --lines 2:3
```

The preview includes `from pathlib import Path`, but lists `normalize` in `unresolved_names`. It does not invent or copy that helper. A preview can succeed while the result still needs another definition.

Even an empty unresolved-name list does not prove standalone execution: imported packages may be missing, imports can have side effects, and a function can rely on runtime state. Relative imports still require the original package context.

## 4. Know when to use another tool

Use your IDE's import-aware copying if it already solves this task. [BetterPy](https://plugins.jetbrains.com/plugin/29896-betterpy) advertises this for JetBrains IDEs and was listed as free extended beta when checked on 7 October 2026. This CLI is an experimental option for work outside an IDE, not a claim of a missing paid IDE feature.

Classes, incomplete selections, wildcard imports, required conditional imports, rebound globals, dynamic namespace lookup and string annotations need manual review. The parser accepts at most 100,000 UTF-8 bytes and 20,000 AST nodes. For a private project, work locally; do not put private source into public feedback.

Stop an active command with **Ctrl+C**. A file named **STOP** beside the script prevents a subsequent preview until you remove that file. No background service is created.

If this helps with a real repeated documentation task, an issue with a fictional or redacted example can describe the manual baseline, correct or missing imports, and actual time spent. A star or download alone does not establish usefulness.

This walkthrough and the tool were created with AI assistance. The commands and stated outputs were checked against the released script using fictional inputs. No customer results are implied. The repository is MIT licensed.
