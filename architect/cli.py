import json
import logging
import os
import re
from collections import defaultdict
from fnmatch import fnmatch

import stdlib_list
from pygments.lexers import get_all_lexers

from architect.utils import scan_imports, ctags, cloc_stats, get_input_folder, run_lizard


def ctags_by_lang_ext(exports, lang_ext='.py'):
    return {k: v for k, v in exports.items() if k.endswith(lang_ext)}


def lang_exts_for(langs):
    lang_exts = []
    ls = [lang.strip() for lang in langs.split(',') if lang.strip()]
    for lang, langs, exts, mimes in get_all_lexers():
        for l in ls:
            if l.lower() in langs or f'*.{l}' in exts:
                lang_exts.extend(exts)
    return lang_exts


def file_match_exts(file, lang_exts):
    return any([fnmatch(file, ext) for ext in lang_exts])


def number(iterable, delimiter='\n\t\t'):
    return delimiter + delimiter.join([f'{n}> {item}' for n, item in enumerate(iterable)])


def analyze_dependency(import_stmt_regex, import_stmt, source_file, possible_target_files, exports):
    """
    Compute the subset of possible_target_files that the source file actually depends on.
    Heuritics to compute the dependency is based on the the language, and semantics of the import statement
    """

    import_stmt = import_stmt.strip()
    input_context = f'import: "{import_stmt}"\n\t for file {os.path.basename(source_file)}, file{source_file}'

    def not_supported():
        return NotImplementedError(input_context)

    def search_targets(target_file_pattern):
        found = [target_file for target_file in possible_target_files if fnmatch(target_file, target_file_pattern)]
        if found:
            logging.info(f'Found [{len(found)}] dependencies for {input_context}: {number(found)}')
        else:
            logging.warning(f'No dependency found for {input_context}, with pattern\n\t\t{target_file_pattern}')
        return found

    match = import_stmt_regex.match(import_stmt)
    if not match:
        return []

    match = [group.replace('"', '').replace(';', '').strip() for group in match.groups()]

    if fnmatch(source_file, '*.ts'):  # Typescript: import {...} from ...
        import_module = match[1]
        if import_module.startswith('./'):
            target_file_pattern = os.path.join(os.path.dirname(source_file), import_module[2:]) + '.*.ts'
            return search_targets(target_file_pattern)
        else:
            raise not_supported()
    elif fnmatch(source_file, '*.py'): # Python (from ...)? import ... (as ...)?

        import_module = match[0]
        if 'as' in import_module:
            import_module = import_module.split('as', maxsplit=1)[0].strip()

        if stdlib_list.in_stdlib(import_module):
            logging.debug(f'Module {import_module} is part python stdlib or built-ins')
            return []

        source_file_parent = source_file
        import_module_copy = import_module
        while True:
            source_file_parent = os.path.dirname(source_file_parent)
            if import_module_copy.startswith('.'):  # resolve relative import
                import_module_copy = import_module_copy[1:]
            else:
                break

        if import_module.startswith('.'):
            target_file_pattern = os.path.join(source_file_parent, import_module_copy + '.py')
        else:
            target_file_pattern = f"**/{import_module.replace('.', '/')}.py"
        return search_targets(target_file_pattern)

    else:
        raise not_supported()

    return set()


def analyze_dependencies(imports, exports):
    """
    imports: Data about what a file declares as its dependency, using an import, include, require etc.
        The exact import syntax and semantic depends on the language.

    exports: Data abaut what a file exports, the things declared in a file
        exports is map (dict) of file to list of ctags from that file
        each ctag dict has token, regex, kind, scope (scope is optional)
        `token` is the textual content of the identifier
        `regex` is a js-style regex that when searched, we can find the line number of code containing this tag
        `kind` is v, f, m, c stands for variable, file, method, class
        `scope` is the parent containing (wrapping) object, class for method,
        a method or function for variable if available

    return:
        Compute a graph of dependency file1 -> file2, if file2 exports something that file1 imports
        Graph is a adjancency list (dict, mapping file to list of files it depends on)
    """

    dependency_graph = defaultdict(set)

    for (import_stmt_regex, langs), file_imports in imports:
        import_stmt_regex = re.compile(import_stmt_regex)
        lang_exts = lang_exts_for(langs)
        possible_target_files = [file for file in exports if file_match_exts(file, lang_exts)]

        for file_import in file_imports:
            source_file = file_import['file']
            import_stmt = file_import['import_stmt']
            target_files = analyze_dependency(import_stmt_regex, import_stmt, source_file, possible_target_files, exports)
            dependency_graph[source_file].update(target_files)

    return {k: list(v) for k, v in dependency_graph.items()}


if __name__ == '__main__':
    print(lang_exts_for('java,py,js,rust,rb,php'))
    folder = get_input_folder('~/cn-sococo-blueprints')
    # size = cloc_stats(folder)
    imports = scan_imports(folder)
    exports = ctags(folder)
    dependencies = analyze_dependencies(imports, exports)
    # metrics = run_lizard(folder)

    json.dump({
        # 'size': size,
        'imports': imports,
        'exports': exports,
        'dependencies': dependencies,
        # 'metrics': metrics,
    }, open('output.json', 'w'), indent=4)