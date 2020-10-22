import concurrent.futures as cf
import json
import logging
from urllib.parse import urlparse

import mistune
import requests
import bs4
from tqdm import tqdm

from rainbow import green, cyan, pink

logging.basicConfig(level=logging.INFO)


def fetch_readme(path, try_files):
    "fetch README.md for a github project, and load it as bs4 soup"
    path = path.strip('/')
    for branch in ('master', 'main'):
        for readme in try_files:
            url = f'https://raw.githubusercontent.com/{path}/{branch}/{readme}'
            page = requests.get(url)
            logging.info(f' ** GET: {page.status_code}, {url}')
            if page.status_code == 200:
                return bs4.BeautifulSoup(mistune.markdown(page.content.decode()), features='lxml')
    logging.warning(f"Could not load README.md file path: {path}")
    return None


def find_topic(ul):
    topic = None
    header = ul.previous_sibling
    while isinstance(header, bs4.element.NavigableString):
        header = header.previous_sibling
    if header is not None and header.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
        topic = header.string
    return topic


def parse_project(li):
    "convert an li element to a project dict"
    a = li.find_all('a') or []
    a = list(a)
    if len(a) == 0:
        logging.warning(f"Found no anchor tag while parsing project: {li}")
        return
    if len(a) > 1:
        if not li.find_all('ul'):
            logging.warning(f"Found more than one anchor tag while parsing project: {li}")
    a = a[0]
    link = a.attrs.get('href', None)
    if link.startswith('#'):  # relative link to same page
        return None
    # if 'github.com' not in link:
    #     return None
    return {
        'project_name': a.string,
        'link': link,
        'description': li.text,
    }


def index_project_link(link, files=('README.md', 'readme.md'), depth=1):
    all_topics = []
    all_projects = []

    logging.info((' >> ' * depth) + green(f'Indexing project: link={link}, files={files}'))

    url = urlparse(link)
    if url.hostname != 'github.com':
        logging.warning(f'Link is not for github.com, will not index: {link}')
        return

    soup = fetch_readme(url.path, files)
    if soup is None:
        return

    lists = soup.find_all('ul')
    for ul in lists:
        projects = []
        for li in ul.find_all('li'):
            project = parse_project(li)
            if project is not None:
                logging.info(pink(f'Found project: {project}'))
                projects.append(project)

        if projects:
            all_projects.extend(projects)
            topic = find_topic(ul)
            if topic is not None:
                logging.info(cyan(f'Found topic: {topic}'))
                for project in projects:
                    project['topic'] = topic
                all_topics.append(topic)

    return {'sub_topics': all_topics, 'sub_projects': all_projects}


def index_project(project):
    link = project['link']
    project.update(index_project_link(link, depth=1))

    try:
        with cf.ThreadPoolExecutor(max_workers=16) as executor:
            futures = {}
            for sub_project in tqdm(project['sub_projects'], desc='Top level indexing'):
                futures[executor.submit(index_sub_projects, sub_project)] = sub_project
            list(tqdm(cf.as_completed(futures), total=len(futures), desc='Top level indexing'))
    except Exception as exc:
        json.dump(awesome_index, open('awesome-index-snapshot.json', 'w'), indent=4)
        raise exc
    return project


def index_sub_projects(sub_project):
    sub_project.update(index_project_link(sub_project['link'], depth=3))

    for sub_sub_project in sub_project['sub_projects']:
        if not sub_sub_project['link'].startswith('https://') \
                and sub_sub_project['link'].endswith('.md'):

            sub_sub_project.update(index_project_link(sub_project['link'], files=[sub_sub_project['link']], depth=3))


if __name__ == '__main__':
    awesome_index = index_project({'project_name': 'Awesome', 'link': 'https://github.com/sindresorhus/awesome'})
    json.dump(awesome_index, open('awesome-index.json', 'w'), indent=4)
else:
    raise Exception("Don't import this! It is meant to be run as script")
