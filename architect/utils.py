import json
import logging
import os
import pathlib
import shlex
import shutil
import subprocess
import tempfile

import lizard
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
                tags.append(line.split('\t'))
    os.chdir(cwd)
    shutil.rmtree(dir)
    return tags


# https://rosettacode.org/wiki/Include_a_file see this for more languages
IMPORT_HINTS = [
    ('import(.*)from(.*)', 'ts'),
    ('import(.*)',  'java,py,go'),
    ('from(.*)import(.*)',  'py'),
    ('use(.*)',  'rust,perl'),
    ('open(.*)',  'ocaml'),
    ('using(.*)',  'csharp'),
    ('source(.*)', 'sh'),
    ('load(.*)', 'clojure,lua'),
     ('library(.*)', 'r'),
    (r'include_once\((.*)\)', 'php'),
    (r'require_once\((.*)\)',  'php'),
    (r'require\((.*)\)', 'js,php,ruby'),
    (r'require(.*)', 'js,php'),
    (r'#\s*include(.*)',  'c,cpp'),
    (r'extern crate(.*)', 'rust'),
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


