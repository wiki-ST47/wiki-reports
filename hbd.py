from datetime import datetime, timedelta
import re
from basereport import BaseReport, UsesWhoisMixin, UsesBlocksMixin

class hbdReport(UsesWhoisMixin, UsesBlocksMixin, BaseReport):
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

    def build_report(self, report_data):
        major_prefixes = report_data['major_prefixes']
        ipblocklist = report_data['ipblocklist']

        page_text = "{{/header}}\n"
        page_text += "{| class='wikitable sortable'\n"
        page_text += "|-\n"
        page_text += "! IP Range\n"
        page_text += "! Blocked IP\n"
        page_text += "! Blocked By\n"
        page_text += "! Blocked Until\n"
        page_text += "! Block Reason\n"
        for prefix, data in sorted(major_prefixes.items(), key=lambda x:self.ip2sort(x[0].split('/')[0])):
            data['currentrangeblocks'] = self.is_currently_blocked(prefix)
            if data['currentrangeblocks']:
                continue
            data['blocklog'] = [x for x in self.homesite.logevents(page="User:"+prefix, logtype="block")]
            first_row = True
            for block in sorted(data['blocks'], key=lambda x:self.ip2sort(x['user'])):
                page_text += "|-\n"
                if first_row:
                    page_text += "| rowspan='"+str(data['count'])+"' | {{checkip|"+prefix+"}}<br>\n"
                    page_text += "[https://tools.wmflabs.org/isprangefinder/hint.php?type=asn&range="+str(data['asn'])+" ASN"+str(data['asn'])+"]<br>\n"
                    page_text += str(data['asnname'])+"<br>\n"
                    page_text += f"{data['count']} directly blocked IPs out of a range of {data['rangesize']}<br>\n"
                    if data['currentrangeblocks']:
                        page_text += "Currently blocked.\n"
                    else:
                        if data['blocklog']:
                            page_text += "Unblocked, but has a block log.\n"
                        else:
                            page_text += "Unblocked, never blocked.\n"
                    first_row = False
                page_text += f"| [[Special:Contributions/{block['user']}|{block['user']}]]\n"
                page_text += f"| [[Special:Contributions/{block['by']}|{block['by']}]]\n"
                page_text += f"| class='nowrap' | {block['expiry']}\n"
                page_text += f"| {self.format_block_reason(block['reason'])}\n"
        page_text += "|}\n"

        self.page_text = page_text
        self.edit_summary = "Automatically updating list"

if __name__ == '__main__':
    report = hbdReport()
    report.run()
