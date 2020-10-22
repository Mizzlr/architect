import concurrent.futures as cf
import csv
import io
import logging

import lizard
from tqdm import tqdm

from architect import duplcode
from architect.utils import find_files, exec_command


def lizard_subprocess(folder, with_duplicate=False, exclude='**/*.min.js'):
    if with_duplicate:
        with_duplicate = '-Eduplicate'
    output = exec_command(f'python3.8 -m lizard {with_duplicate} -x"{exclude}" --csv {folder}')

    complexity = []
    duplicate_blocks = []
    duplicate_block = []
    duplicate_started = False

    total_duplicate_rate = None
    total_unique_rate = None

    for line in output.splitlines(keepends=False):
        if duplicate_started:
            if line.startswith('Total duplicate rate:'):
                total_duplicate_rate = float(line.split(':')[1].split('%')[0].strip())
                continue
            if line.startswith('Total unique rate:'):
                total_unique_rate = float(line.split(':')[1].split('%')[0].strip())
                continue

            if line == '--------------------------':
                duplicate_block = []
            elif line == '^^^^^^^^^^^^^^^^^^^^^^^^^^':
                duplicate_blocks.append(duplicate_block)
                duplicate_block = []
            else:
                duplicate_block.append(line)
        else:
            complexity.append(line)
            if with_duplicate and not duplicate_started:
                if line.startswith('Duplicates'):
                    duplicate_started = True

    rows = []
    for row in csv.DictReader(io.StringIO('\n'.join(complexity)), fieldnames=[
        'code', 'complexity', 'tokens', 'params', 'lines', 'location', 'file',
        'method_name', 'method_signature', 'start_line', 'end_line']):

        row['code'] = int(row['code'])
        row['complexity'] = int(row['complexity'])
        row['tokens'] = int(row['tokens'])
        row['params'] = int(row['params'])
        row['lines'] = int(row['lines'])
        row['start_line'] = int(row['start_line'])
        row['end_line'] = int(row['end_line'])

        rows.append(row)

    return {
        'complexity': rows,
        'duplicate_blocks': duplicate_blocks,
        'total_duplicate_rate': total_duplicate_rate,
        'total_unique_rate': total_unique_rate
    }


def main():
    import lizard
    file = '../qretail/QRetail-Legacy-GuitarCenter-GcAlrUiCore/src/main/webapp/Common/DataHandling/eba.callback.js'
    return list(lizard.analyze_files([file], exts=lizard.get_extensions([]) + [duplcode.LizardExtension()]))


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


def run_lizard(folder, concurrency=4):
    duplcode_ext = duplcode.LizardExtension()
    from importlib import import_module as im
    wordcount_ext = im('lizard_ext.lizardwordcount').LizardExtension()

    extensions = lizard.get_extensions(['mccabe', 'nd']) + [duplcode_ext, wordcount_ext]
    files = find_files(folder, for_lizard=True)
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
                complexity_by_file[file] = future.result()

        list(duplcode_ext.cross_file_process(complexity_by_file.values()))

        duplicate_blocks = []
        for duplicate_block in tqdm(duplcode_ext.get_duplicates(), desc='Analyzing duplicate code:'):
            duplicate_blocks.append([snippet.to_dict() for snippet in duplicate_block])

        logging.info(f'Total duplicate blocks: {len(duplicate_blocks)}')
        logging.info("Total duplicate rate: %.2f%%" % (duplcode_ext.duplicate_rate() * 100))
        logging.info("Total unique rate: %.2f%%" % (duplcode_ext.unique_rate() * 100))

        return {
            'complexity_by_file': {k: file_info_to_dict(v) for k, v in complexity_by_file.items()},
            'duplicate_blocks': duplicate_blocks,
            'duplicate_rate': duplcode_ext.duplicate_rate(),
            'unique_rate': duplcode_ext.unique_rate()
        }



