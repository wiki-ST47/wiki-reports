from datetime import datetime, timedelta
import re
from basereport import (BaseReport, UsesWhoisMixin, UsesBlocksMixin,
                        TwoLevelTableMixin)

class hbdReport(TwoLevelTableMixin, UsesWhoisMixin, UsesBlocksMixin, BaseReport):
    page_name = "User:ST47/high_block_density"

    def get_prefix(self, block):
        return '.'.join(block.split('.')[0:3])

    def gather_data(self):
        site = self.homesite
        report_data = super().gather_data()

        ipblocklist = report_data['ipblocklist']
        interestingv4blocks = [
            x for x in ipblocklist
            if '.' in x['user']
            and re.search("proxy|proxies|webhost", x['reason'], flags=re.I)
            and x['rangestart'] == x['rangeend']]

        prefix_data = {}
        for block in interestingv4blocks:
            asn, prefix = self.whois.get_asn_netmask(block['rangestart'])
            asnname = self.whois.get_name_by_ip(block['rangestart'])
            if prefix is None:
                continue
            ip, cidr = prefix.split('/')
            cidr = int(cidr)
            if prefix not in prefix_data:
                prefix_data[prefix] = {
                    'prefix': prefix,
                    'count': 0,
                    'blocks': [],
                    'asn': asn,
                    'asnname': asnname,
                    'rangebase': ip,
                    'rangecidr': cidr,
                    'rangesize': 2 ** (32-cidr),
                }
            prefix_data[prefix]['count'] += 1
            prefix_data[prefix]['blocks'].append(block)

        major_prefixes = {k:v for (k,v) in prefix_data.items() if v['count'] >= 15 and v['count']/v['rangesize'] > 0.07}

        report_data['major_prefixes'] = major_prefixes

        return report_data

    def ip2sort(self, ip):
        components = ip.split('.')
        sortkey = '.'.join(map(lambda x:"%03d" % (int(x)), components))
        return sortkey

    def get_row_iterator(self, report_data):
        return sorted(report_data['major_prefixes'].values(), key=lambda x:self.ip2sort(x['prefix'].split('/')[0]))

    def get_subrow_iterator(self, row):
        return sorted(row['blocks'], key=lambda x:self.ip2sort(x['user']))

    def format_iprange(self, row, subrow):
        row['blocklog'] = [x for x in self.homesite.logevents(page="User:"+row['prefix'], logtype="block")]
        res  = "{{checkip|"+row['prefix']+"}}<br>\n"
        res += "[https://tools.wmflabs.org/isprangefinder/hint.php?type=asn&range="+str(row['asn'])+" ASN"+str(row['asn'])+"]<br>\n"
        res += str(row['asnname'])+"<br>\n"
        res += f"{row['count']} directly blocked IPs out of a range of {row['rangesize']}<br>\n"
        if self.is_currently_blocked(row['prefix']):
            res += "Currently blocked."
        else:
            if row['blocklog']:
                res += "Unblocked, but has a block log."
            else:
                res += "Unblocked, never blocked."
        return res

    columns = [
        {
            'header': "IP Range",
            'grouped': True,
            'formatter': format_iprange,
        }, {
            'header': "Blocked IP",
            'formatter': lambda self,row,subrow: f"[[Special:Contributions/{subrow['user']}|{subrow['user']}]]",
        }, {
            'header': "Blocked By",
            'formatter': lambda self,row,subrow: f"[[Special:Contributions/{subrow['by']}|{subrow['by']}]]",
        }, {
            'header': "Blocked Until",
            'css': "class='nowrap'",
            'formatter': lambda self,row,subrow: subrow['expiry'],
        }, {
            'header': "Block Reason",
            'formatter': lambda self,row,subrow: f"{self.format_block_reason(subrow['reason'])}",
        }
    ]

    def build_row(self, row):
        if self.is_currently_blocked(row['prefix']):
            return ""
        return super().build_row(row)


if __name__ == '__main__':
    report = hbdReport()
    report.run()
