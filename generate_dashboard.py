#!/usr/bin/env python3

from __future__ import print_function, absolute_import

import json


def build_var(name, values):
    return {
        "allFormat": "glob",
        "current": {
          "tags": [],
          "text": ' + '.join(values),
          "value": values,
        },
        "datasource": None,
        "includeAll": False,
        "multi": True,
        "multiFormat": "glob",
        "name": name,
        "options": [{
            'selected': True,
            'text': value,
            'value': value,
            } for value in values],
        "query": ','.join(values),
        "refresh_on_load": False,
        "type": "custom"
      }


def serialize_dashboard(output, dashboard):
    json.dump(dashboard, output, indent=2, sort_keys=True)


def deepcopy(structure):
    return json.loads(json.dumps(structure))


def render_dashboard(template, title, nodes, uplinks):
    template = deepcopy(template)
    template['title'] = title
    template['templating']['list'] = [
        build_var('nodes', nodes),
        build_var('uplinks', uplinks),
    ]
    return template


def main():
    import argparse
    import locale
    import os

    os.environ['TZ'] = 'UTC'
    os.environ['LC_ALL'] = 'en_US.UTF-8'
    locale.setlocale(locale.LC_ALL, '')

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument('--title', '-t', default='Dashboard',
                        help='Title of the dashboard')
    parser.add_argument('--nodes', '-n', nargs='*', metavar='NODEID',
                        default=[], help='Nodes of the network')
    parser.add_argument('--uplinks', '-u', nargs='*', metavar='NODEID',
                        default=[], help='Uplinks of the network')
    parser.add_argument('--template', '-e', default='dashboard-template.json',
                        type=argparse.FileType('r'),
                        help='Template to generate the dashboard from')
    parser.add_argument('--config', '-c',
                        help='Read nodes and uplinks from a config file')

    parser.add_argument(
            '--output', '-o',
            type=argparse.FileType('w'),
            default='-',
            help='where to write the output')

    args = parser.parse_args()

    template = json.load(args.template)

    dashboard = render_dashboard(template, args.title,
                                 args.nodes, args.uplinks)
    serialize_dashboard(args.output, dashboard)

if __name__ == '__main__':
    main()
