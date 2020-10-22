import json
import sys

from architect.complexity import run_lizard
from architect.utils import scan_imports, ctags, cloc_stats

if __name__ == '__main__':
    folder = sys.argv[1]

    size = cloc_stats(folder)
    imports = scan_imports(folder)
    exports = ctags(folder)
    metrics = run_lizard(folder)
    json.dump({
        'size': size,
        'imports': imports,
        'exports': exports,
        'metrics': metrics,
    }, open('output.json', 'w'), indent=4)