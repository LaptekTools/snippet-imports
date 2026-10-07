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
