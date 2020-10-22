import concurrent.futures as cf
import logging

import lizard
from tqdm import tqdm

import architect.utils
from architect.utils import find_files


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
    files = find_files(folder, for_lizard=True, lang_ext='.py')
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

        # options = lizard.parse_args(['dummy'])
        # result = complexity_by_file.values()
        # schema = lizard.OutputScheme(extensions)
        # lizard.print_result(result, options, schema, lizard.AllResult)
        # lizard.print_extension_results(extensions)
        return lizard_metrics
