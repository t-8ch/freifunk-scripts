#!/usr/bin/env python3

from __future__ import print_function, absolute_import

import collections
import datetime
import ipaddress
import textwrap

# atomic

address_records = {
    4: 'A',
    6: 'AAAA',
}

ZoneSettings = collections.namedtuple('ZoneSettings', [
    'origin', 'default_ttl',
    'ns', 'postmaster',
    'refresh', 'retry', 'expire', 'min_ttl',
    'nameservers',
])


def iso_to_serial(iso):
    return datetime.datetime.strptime(
            iso, '%Y-%m-%dT%H:%M:%S').strftime('%s')


def format_record(id, subdomain, type, value):
    if subdomain is not None:
        subdomain = subdomain.lstrip('.')
        id = '{}.{}'.format(id, subdomain)

    value = str(value)
    id = id.rstrip('.').encode('idna').lower()

    if ';' in value:
        value = '"' + value + '"'

    return '{:<30} IN {:<4} {}'.format(
            id, type, value)


def format_address_record(id, subdomain, address):
    address = ipaddress.ip_address(address)

    return format_record(
            id, subdomain, address_records[address.version], address)


def separator(output):
    output.write('\n')


class SubdomainNet(object):
    SEPARATOR = '|'

    def __init__(self, subdomain, net):
        self.subdomain = subdomain
        self.net = ipaddress.ip_network(net)

    @classmethod
    def parse(cls, value):
        s, n = value.split(cls.SEPARATOR, 1)
        return cls(s, n)

    def __str__(self):
        return '{}{}{}'.format(
                self.subdomain or '', self.SEPARATOR, self.net)

    def __repr__(self):
        return '{}{}{}'.format(
                self.subdomain or '', self.SEPARATOR, self.net)


def create_nodes_zone(output, nodes, zone_settings, subdomain_nets,
                      map_template):
    nodes_json = fetch_nodes(nodes)
    write_zone(output, nodes_json, zone_settings, subdomain_nets, map_template)


def fetch_nodes(path_or_url):
    if (path_or_url.startswith('http://') or
            path_or_url.startswith('https://')):

        import requests
        r = requests.get(path_or_url, headers={
            'User-Agent': (
                'https://github.com/t-8ch/'
                'freifunk-scripts/blob/master/nodes2zone.py'
            ),
        })
        r.raise_for_status()
        return r.json()

    else:
        with open(path_or_url, 'r') as f:
            import json
            return json.loads(f)


def write_zone(output, nodes_json, zone_settings, subdomain_nets,
               map_template):
    zs = zone_settings

    serial = iso_to_serial(nodes_json['timestamp'])

    output.write(textwrap.dedent(
        '''
        $ORIGIN {}
        $TTL    {}

        @ IN SOA {} {} (
            {:<20} ; serial number
            {:<20} ; Refresh
            {:<20} ; Retry
            {:<20} ; Expire
            {:<20} ; Min TTL
        )

        ''').format(
            zs.origin, zs.default_ttl,
            zs.ns, zs.postmaster,
            serial, zs.refresh, zs.retry, zs.expire, zs.min_ttl))

    for ns in zone_settings.nameservers:
        output.write(format_record('@', None, 'NS', ns))
        separator(output)

    separator(output)

    for sn in subdomain_nets:
        subdomain, network = sn.subdomain, sn.net
        for node in nodes_json['nodes']:
            nodeinfo = node['nodeinfo']
            hostname = nodeinfo['hostname']
            node_id = nodeinfo['node_id']
            mac = nodeinfo['network']['mac']

            for address in nodeinfo['network'].get('addresses', []):
                address = ipaddress.ip_address(address)
                if address in network:
                    if map_template:
                        link = map_template.format(
                                hostname=hostname, node_id=node_id, mac=mac)
                    else:
                        link = None

                    output.write(format_address_record(
                        hostname, subdomain, address))
                    separator(output)

                    output.write(
                            format_record(hostname, subdomain, 'TXT', link))
                    separator(output)

                    if hostname != node_id:
                        output.write(
                                format_address_record(
                                    node_id, subdomain, address))
                        separator(output)

                        output.write(
                                format_record(node_id, subdomain, 'TXT', link))
                        separator(output)

                    separator(output)


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

    parser.add_argument(
        '--nodes', '--nodes-file', '--nodes-url', '-n',
        default='http://map.ffm.freifunk.net/nodes.json',
        help='nodes.json used by meshviewer',
    )
    parser.add_argument(
        '--map-template', '-t',
        default='http://map.ffm.freifunk.net/#!v:g;n:{node_id}',
        nargs='*',
        help='''
        templates to generate links for single nodes, these are added in TXT
        records. `node_id`, `hostname` and `macaddress` may be interpolated'
        ''')
    parser.add_argument('--origin', '-g', default='nodes.freifunk.t-8ch.de.',
                        help='$ORIGIN added to zone')
    parser.add_argument('--default-ttl', '-d', type=int, default=86400,
                        help='$TTL added to zone')
    parser.add_argument('--ns', '-s', default='ns1.t-8ch.de.',
                        help='primary nameserver for SOA')
    parser.add_argument('--postmaster', '-p',
                        default='freifunk+dns.t-8ch.de.',
                        help='primary nameserver for SOA')
    parser.add_argument('--refresh', '-r', type=int, default=28800,
                        help='refresh for SOA')
    parser.add_argument('--retry', '-y', type=int, default=7200,
                        help='retry for SOA')
    parser.add_argument('--expire', '-x', type=int, default=864000,
                        help='expire for SOA')
    parser.add_argument('--min-ttl', '-m', type=int, default=86400,
                        help='minimum TTL for SOA')
    parser.add_argument('--nameservers', '-v', nargs='*',
                        default=['ns1.t-8ch.de.', 'ns2.t-8ch.de.'],
                        help='nameservers responsible for this zone')
    parser.add_argument(
            '--subdomain-net', nargs='*',
            default=[SubdomainNet(None, 'fddd:5d16:b5dd:0::/64')],
            type=SubdomainNet.parse,
            help='''
            Mappings for address subnets to subdomains, the format is
            <subdomain>{}<subnet>, subdomain may be empty
            '''.format(SubdomainNet.SEPARATOR))

    parser.add_argument(
            '--output', '-o',
            type=argparse.FileType('w'),
            default='-',
            help='where to write the output')

    args = parser.parse_args()

    zone_settings = ZoneSettings(
            origin=args.origin, default_ttl=args.default_ttl,
            ns=args.ns, postmaster=args.postmaster,
            refresh=args.refresh, retry=args.retry, expire=args.expire,
            min_ttl=args.min_ttl, nameservers=args.nameservers)

    create_nodes_zone(
            args.output, args.nodes, zone_settings, args.subdomain_net,
            args.map_template)

if __name__ == '__main__':
    main()
