import json
import logging
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent import futures as cf

import lizard
from lizard_ext import lizardduplicate
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)


def find_files(folder, lang_ext='', for_lizard=False):
    files = []
    languages = lizard.languages()
    for file in pathlib.Path(folder).glob(f'**/*{lang_ext}'):
        file = str(file)
        if not file.endswith('.min.js'):
            if for_lizard:
                if any([lang.match_filename(file) for lang in languages]):
                    files.append(file)
            else:
                files.append(file)
    return files


def exec_command(command):
    logging.info(f'Executing command: {command}')
    output = subprocess.check_output(shlex.split(command))
    return output.decode()


def cloc_stats(folder):
    output = exec_command(f'tokei --files -o json "{folder}"')
    return json.loads(output)['inner']


def ctags(folder, languages='ada,c,c#,c++,clojure,cobol,elixir,erlang,fortran,go,java,javascript,lua,matlab,ocaml'
                            ',perl,perl6,php,protobuf,python,r,ruby,rust,sh,sql,tcl,typescript,verilog,xml'):
    dir = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(dir)
    exec_command(f'ctags -R --output-format=u-ctags --languages="{languages}" --totals {folder}')
    tags = defaultdict(list)
    preamble = True
    with open('tags', 'rb') as tags_file:
        for line in tags_file:
            line = line.decode(errors='ignore').strip()
            if not line.startswith('!_TAG'):
                preamble = False
            if not preamble:
                parts = line.split('\t')
                if len(parts[-1]) == 1:
                    kind = parts[-1]
                    scope = None
                else:
                    kind = parts[-2]
                    scope = parts[-1]
                file = parts[1]
                tag = dict(token=parts[0], regex=parts[2], kind=kind, scope=scope)
                tags[file].append(tag)
    os.chdir(cwd)
    shutil.rmtree(dir)
    return {k: v for k, v in tags.items()}


# https://rosettacode.org/wiki/Include_a_file see this for more languages
IMPORT_HINTS = [
    (r'\bimport\b(.*)\bfrom\b(.*)', 'ts'),
    (r'\bimport\b(.*)',  'java,py,go'),
    (r'\bfrom\b(.*)\bimport\b(.*)',  'py'),
    (r'\buse\b(.*)',  'rust,perl'),
    (r'\bopen\b(.*)',  'ocaml'),
    (r'\busing\b(.*)',  'csharp'),
    (r'\bsource\b(.*)', 'sh'),
    (r'\bload\b(.*)', 'clojure,lua,ruby'),
    (r'\blibrary\b(.*)', 'r'),
    (r'\binclude_once\((.*)\)', 'php'),
    (r'\brequire_once\((.*)\)',  'php'),
    (r'\brequire\((.*)\)', 'js,php,ruby'),
    (r'\brequire\b(.*)', 'js,ruby'),
    (r'#?\s*include\b(.*)',  'c,cpp,ruby'),
    (r'\bextern crate\b(.*)', 'rust'),
    (r'\bextend\b(.*)', 'ruby'),
]


def scan_imports(folder):
    all_imports = {}

    for regex, lang in tqdm(IMPORT_HINTS, desc='Scanning imports'):
        lang_types = ' '.join([f'-t {lang.strip()}' for lang in lang.split(',') if lang.strip()])
        imports = []
        try:
            output = exec_command(f'rg --no-ignore --glob "!**/*.min.js" {lang_types} "{regex}" {folder}')
            for line in output.splitlines(keepends=False):
                file, import_stmt = line.split(':', maxsplit=1)
                imports.append(dict(file=file, import_stmt=import_stmt))
        except subprocess.CalledProcessError:
            logging.debug(f'Silently ignoring no match for {lang}, {regex}')

        all_imports[(regex, lang)] = imports
    return list(all_imports.items())


class DuplcodeExtension(lizardduplicate.LizardExtension):
    def _unified_token(self, token):
        if not token:
            return token
        return super(DuplcodeExtension, self)._unified_token(token)


def get_input_folder(default):
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = default
    if folder.startswith('~'):
        folder = os.path.expanduser(folder)
    folder = os.path.abspath(os.path.normpath(folder))
    return folder


def func_info_to_dict(func_info: lizard.FunctionInfo):
    return {
        'func_name': func_info.name,
        'func_signature': func_info.long_name,
        'start_line': func_info.start_line,
        'end_line': func_info.end_line,
        'lines': func_info.nloc,
        'complexity': func_info.cyclomatic_complexity,
        'max_nesting_depth': func_info.max_nesting_depth,
    }


def file_info_to_dict(file_info: lizard.FileInformation):
    return {
        'file': file_info.filename,
        'lines': file_info.nloc,
        'tokens': file_info.token_count,
        'avg_lines': file_info.average_nloc,
        'avg_tokens': file_info.average_token_count,
        'avg_complexity': file_info.average_cyclomatic_complexity,
        'sum_complexity': file_info.CCN,
        'sum_max_nesting_depth': file_info.ND,
        'word_count': file_info.wordCount,
        'functions': [func_info_to_dict(func) for func in file_info.function_list],
    }


def snippet_to_dict(snippet):
    return {'file': snippet.file_name, 'start_line': snippet.start_line, 'end_line': snippet.end_line}


def run_lizard(folder, concurrency=4, find_duplicates=True):
    duplcode_ext = architect.utils.DuplcodeExtension()
    from importlib import import_module as im
    wordcount_ext = im('lizard_ext.lizardwordcount').LizardExtension()

    extensions = lizard.get_extensions(['mccabe', 'nd']) + [wordcount_ext]
    if find_duplicates:
        extensions.append(duplcode_ext)

    # extensions = [lizard.preprocessing, lizard.line_counter, duplcode_ext]
    files = find_files(folder, for_lizard=True, lang_ext='')
    file_analyzer = lizard.FileAnalyzer(extensions)

    with cf.ProcessPoolExecutor(max_workers=concurrency) as executor:
        futures = {}
        complexity_by_file = {}

        for file in files:
            futures[executor.submit(file_analyzer, file)] = file

        for future in tqdm(cf.as_completed(futures), total=len(futures), desc='Analyzing complexity in files'):
            file = futures[future]
            logging.debug(f'Analyzed complexity for file: {file}')
            if future._exception:
                logging.warning(f'Failed to analyze complexity for file: {file}')
            else:
                file_info: lizard.FileInformation = future.result()
                complexity_by_file[file] = file_info

        lizard_metrics = {'complexity_by_file': {k: file_info_to_dict(v) for k, v in complexity_by_file.items()}}
        if find_duplicates:
            list(duplcode_ext.cross_file_process(complexity_by_file.values()))

            duplicate_blocks = []
            for duplicate_block in tqdm(duplcode_ext.get_duplicates(), desc='Analyzing duplicate code:'):
                duplicate_blocks.append([snippet_to_dict(snippet) for snippet in duplicate_block])

            logging.info(f'Total duplicate blocks: {len(duplicate_blocks)}')
            logging.info("Total duplicate rate: %.2f%%" % (duplcode_ext.duplicate_rate() * 100))
            logging.info("Total unique rate: %.2f%%" % (duplcode_ext.unique_rate() * 100))

            lizard_metrics.update({
                'duplicate_blocks': duplicate_blocks,
                'duplicate_blocks_count': len(duplicate_blocks),
                'duplicate_rate': duplcode_ext.duplicate_rate(),
                'unique_rate': duplcode_ext.unique_rate()
            })
        return lizard_metrics