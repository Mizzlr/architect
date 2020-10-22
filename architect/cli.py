import json
import re
from collections import defaultdict
from fnmatch import fnmatch

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


def analyze_dependency(import_stmt_regex, import_stmt, source_file, possible_target_files, exports):
    """
    Compute the subset of possible_target_files that the source file actually depends on.
    Heuritics to compute the dependency is based on the the language, and semantics of the import statement
    """

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