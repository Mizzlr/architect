import glob
import json
import pathlib
import shlex
import subprocess
import logging
import lizard

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

    # return lizard.get_all_source_files([folder], exclude_patterns='**/*.min.js', lans=None)


def exec_command(command):
    logging.info(f'Executing command: {command}')
    output = subprocess.check_output(shlex.split(command))
    return output.decode()


def cloc_stats(folder):
    output = exec_command(f'tokei --files -o json "{folder}"')
    return json.loads(output)['inner']