import json

from architect.complexity import run_lizard
from architect.utils import scan_imports, ctags, cloc_stats, get_input_folder

if __name__ == '__main__':
    folder = get_input_folder('~/cn-sococo-blueprints')
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