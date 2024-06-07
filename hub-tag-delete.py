#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A script for cleaning up deprecated image tags on Docker Hub

This script parses a list of tags with deletion dates from a source document
and deletes them from the Docker Hub if they are present and the current date
has passed the specified deletion date.

The source for listing tags and their deletion dates can be a JSON file and/or
Markdown document. The Markdown source parses a table within specified
comment tags.

The source tag list supports wildcards. For example, '1.*' would match anything
beginning with '1.'. Refer to Python's 'fnmatch' module for more information
on wildcards: https://docs.python.org/3/library/fnmatch.html

Configuration is set using environment variables.

* Refer to the README.md file in this project's root directory for usage
    information.

* Refer to the LICENSE file in this project's root for license information.

Todo:
    * Improve output (show scheduled date)
    * Support GitLab registry
    * CLI arguments

"""

import os
import json
import fnmatch
from datetime import datetime

import requests

config = {
    'date_format': os.environ.get('DATE_FORMAT', '%B %d, %Y'),
    'docker_hub': {
        'api_base_url': os.environ.get('DOCKERHUB_API_BASE_URL',
                                       'https://hub.docker.com/v2'),
        'username': os.environ.get('DOCKERHUB_USERNAME'),
        'password': os.environ.get('DOCKERHUB_PASSWORD')
    },
    'json': {
        'file': os.environ.get('JSON_FILE')
    },
    'markdown': {
        'file': os.environ.get('MARKDOWN_FILE'),
        'format': 'table',  # only 'table' is available currently.
        'begin_string': os.environ.get('MARKDOWN_BEGIN_STRING',
                                       '<!-- BEGIN deletion_table -->'),
        'end_string': os.environ.get('MARKDOWN_END_STRING',
                                     '<!-- END deletion_table -->'),
        'tag_column': os.environ.get('MARKDOWN_TAG_COLUMN', 1),
        'date_column': os.environ.get('MARKDOWN_DATE_COLUMN', 2)
    }
}

org, repo = os.environ.get('DOCKERHUB_REPOSITORY').split('/')
config['docker_hub']['organization'] = org
config['docker_hub']['repository'] = repo

now = datetime.now()
session = requests.Session()


def line_is_ignored(line):
    """Check if a line from Markdown should be ignored"""
    ignore_lines = [
        config['markdown']['begin_string'],
        config['markdown']['end_string']
    ]
    for ignore in ignore_lines:
        if line.startswith(ignore):
            return True
    return False


def get_readme_table():
    """Return rows from a Markdown table that list tag patterns and deletion
        dates
    """
    md_file = open(config['markdown']['file'], 'r').readlines()
    parsing = False
    items = []
    linenum = 0
    for line in md_file:
        if line.startswith(config['markdown']['begin_string']):
            parsing = True
        if parsing:
            if line.startswith('|') and not line_is_ignored(line):
                # ignore empty lines
                if line.strip():
                    linenum += 1
                    # Skip the header and separator (first two lines)
                    if linenum > 2:
                        items.append(parse_md_line(line))
        if line.startswith(config['markdown']['end_string']):
            parsing = False

    return items


def parse_date(date):
    """Parse a date string and return a datetime object"""
    return datetime.strptime(date, config['date_format'])


def parse_md_line(md_line):
    """Extract tag patterns and expiration dates from a Markdown table row"""
    md = md_line.strip().split('|')

    if int(config['markdown']['tag_column']) > (len(md) - 1):
        raise IndexError('tag column is out of range.')
    if int(config['markdown']['date_column']) > (len(md) - 1):
        raise IndexError('date column is out of range.')

    # Determine which table column the tags and date are in
    tags = md[int(config['markdown']['tag_column'])]
    date = md[int(config['markdown']['date_column'])]

    tags = tags.strip().replace('`', '')
    date = date.strip()
    tags = tags.split(',')
    return {'tags': tags, 'date': date}


def json_tags():
    """Load a JSON file with tag deletions specified."""
    with open(config['json']['file'], 'r') as f:
        data = list(json.load(f))
        return data


def get_tag_list():
    """Returns a list of tag patterns from the source"""
    tags = []
    if config['json']['file']:
        tags.append(json_tags())
    if config['markdown']['file']:
        tags.append(get_readme_table())
    tags = [i for row in tags for i in row]
    return tags


def tags_to_delete():
    """Return a list of tags to delete based on the deletion date"""
    tags_list = []
    for item in get_tag_list():
        if now >= parse_date(item['date']):
            for pattern in item['tags']:
                pattern = pattern.strip()
                t = tags_matching_pattern(pattern)
                tags_list.append(t)
    # Flatten list
    if len(tags_list) > 0:
        tags_list = [i for row in tags_list for i in row]
    return tags_list


def delete_expired_tags():
    """Delete tags from the Docker Hub registry using the API"""
    deleted = []

    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {docker_hub_token()}"
    }

    for tag in tags_to_delete():
        url = '/namespaces/' + config['docker_hub']['organization'] \
                + '/repositories/' + config['docker_hub']['repository'] \
                + '/tags/' + tag

        resp = session.delete(
            config['docker_hub']['api_base_url'] + url,
            headers=headers
        )
        resp.raise_for_status()
        deleted.append(tag)
    return deleted


def docker_hub_token():
    """Return an auth token for the Docker Hub API"""
    headers = {"Content-type": "application/json"}
    body = json.dumps({
        'username': config['docker_hub']['username'],
        'password': config['docker_hub']['password']
    })
    auth = session.post(config['docker_hub']['api_base_url'] + '/users/login',
                        headers=headers, data=body)
    auth.raise_for_status()
    content = auth.json()
    return content['token']


def tags_matching_pattern(pattern):
    """Compares tags on Docker Hub to our tag patterns and returns a list of
        matching tags that are on Docker Hub
    """
    url = '/namespaces/' \
        + config['docker_hub']['organization'] \
        + '/repositories/' \
        + config['docker_hub']['repository'] + '/tags'

    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {docker_hub_token()}"
    }

    params = {
        'page_size': 100,
        'ordering': 'name'
    }

    resp = session.get(
        config['docker_hub']['api_base_url'] + url,
        headers=headers,
        params=params
    )
    _next = None
    matching_tags = []
    # Loop through pagination
    while True:
        if _next:
            resp = session.get(_next, headers=headers)
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # Handle the 404 error here
                    break
                raise

        resp = resp.json()
        for i in resp['results']:
            if fnmatch.fnmatch(i['name'], pattern):
                matching_tags.append(i['name'])

        if resp['next']:
            _next = resp['next']
            continue

        return matching_tags


if __name__ == "__main__":
    _tags = tags_to_delete()
    if len(_tags) > 0:
        delete_expired_tags()
        for _tag in _tags:
            img_tag = config['docker_hub']['organization'] + '/' \
                    + config['docker_hub']['repository'] + ':' + _tag
            print(f"> Deleted {img_tag}")
    else:
        print("There are no tags to delete.")
