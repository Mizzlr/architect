import json
import logging
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile

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
    tags = []
    preamble = True
    with open('tags', 'rb') as tags_file:
        for line in tags_file:
            line = line.decode(errors='ignore').strip()
            if not line.startswith('!_TAG'):
                preamble = False
            if not preamble:
                parts = line.split('\t')
                scope = parts[5] if len(parts) > 5 else None
                kind = parts[4] if len(parts) > 4 else parts[-1]
                tag = dict(token=parts[0], file=parts[1], regex=parts[3], kind=kind, scope=scope)
                tags.append(tag)
    os.chdir(cwd)
    shutil.rmtree(dir)
    return tags


# https://rosettacode.org/wiki/Include_a_file see this for more languages
IMPORT_HINTS = [
    (r'\bimport\b(.*)\bfrom\b(.*)', 'ts'),
    (r'\bimport\b(.*)',  'java,py,go'),
    (r'\bfrom\b(.*)\bimport\b(.*)',  'py'),
    (r'\buse\b(.*)',  'rust,perl'),
    (r'\bopen\b(.*)',  'ocaml'),
    (r'\busing\b(.*)',  'csharp'),
    (r'\bsource\b(.*)', 'sh'),
    (r'\bload\b(.*)', 'clojure,lua'),
    (r'\blibrary\b(.*)', 'r'),
    (r'\binclude_once\((.*)\)', 'php'),
    (r'\brequire_once\((.*)\)',  'php'),
    (r'\brequire\((.*)\)', 'js,php,ruby'),
    (r'\brequire\b(.*)', 'js,php'),
    (r'#\s*include\b(.*)',  'c,cpp'),
    (r'\bextern crate\b(.*)', 'rust'),
]


def scan_imports(folder):
    imports = {}

    for regex, lang in tqdm(IMPORT_HINTS, desc='Scanning imports'):
        try:
            output = exec_command(f'rg -t {lang} "{regex}" {folder}').splitlines(keepends=False)
        except subprocess.CalledProcessError:
            logging.debug(f'Silently ignoring no match for {lang}, {regex}')
            output = []
        imports[(regex, lang)] = output

    return list(imports.items())


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