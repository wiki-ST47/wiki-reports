import pywikibot
from flare.tools.whoisip import WhoisLookup
import pyasn
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import random
import re
from basereport import BaseReport, UsesWhoisMixin, UsesBlocksMixin


class rbesReport(UsesBlocksMixin, UsesWhoisMixin, BaseReport):
    page_name = "User:ST47/rangeblocks_expiring_soon"

    def gather_data(self):
        site = self.homesite
        report_data = super().gather_data()

        coloranges = report_data['coloranges']

        enrichedv4coloranges = []
        enrichedv6coloranges = []
        for x in coloranges:
            x['asn'] = self.whois.get_asn(x['rangestart'])
            x['asnname'] = self.whois.get_name_by_ip(x['rangestart'])
            if '.' in self.get_block_target(x):
                x['ipcount'] = 2 ** (32 - (int(self.get_block_target(x).split('/')[1])))
                enrichedv4coloranges.append(x)
            else:
                x['ipcount'] = 2 ** (64 - (int(self.get_block_target(x).split('/')[1])))
                enrichedv6coloranges.append(x)

        threshold = (datetime.now() + timedelta(days=20)).strftime("%Y-%m-X")
        expiringsoon = [x for x in coloranges if x['expiry'] <= threshold and x['ipcount'] > 1]
        expiringsoon.sort(key=lambda x:x['expiry'])

        report_data['coloranges'] = coloranges
        report_data['expiringsoon'] = expiringsoon
        return report_data

    def get_block_target(self, block):
        return block['user']

    def build_block_links(self, user):
        random.seed(user)
        res  = "[https://en.wikipedia.org/wiki/Special:Block/"+user+"?wpExpiry="+str(random.randint(10,14))+"%20months&wpHardBlock=1 ~1 YEAR]<br>"
        res += "[https://en.wikipedia.org/wiki/Special:Block/"+user+"?wpExpiry="+str(random.randint(30,42))+"%20months&wpHardBlock=1 ~3 YEARS]"
        return res

    def format_asn(self, block):
        if block['asn']:
            return "[https://tools.wmflabs.org/isprangefinder/hint.php?type=asn&range="+str(block['asn'])+" ASN"+str(block['asn'])+"]<br>"+block['asnname']
        return ""

    columns = [
        {
            'header': "IP Range",
            'formatter': lambda self,row:"{{checkip|"+self.get_block_target(row)+"}}",
        }, {
            'header': "ASN",
            'formatter': format_asn,
        }, {
            'header': "Blocked By",
            'formatter': lambda self,row:f"[[Special:Contributions/{row['by']}|{row['by']}]]"
        }, {
            'header': "Blocked Until",
            'css': "class='nowrap'",
            'formatter': lambda self,row:row['expiry'],
        }, {
            'header': "Block Reason",
            'formatter': lambda self,row:self.format_block_reason(row['reason']),
        }, {
            'header': "Reblock",
            'css': "class='nowrap'",
            'formatter': lambda self,row:self.build_block_links(self.get_block_target(row)),
        }
    ]

    def get_row_iterator(self, report_data):
        return report_data['expiringsoon']

    def build_report(self, report_data):
        super().build_report(report_data)

        def page_text_to_range_list(text):
            return [m for m in re.findall('\{\{checkip|([0-9a-f.:/]+)\}\}', text, re.I)]

        old_ranges = page_text_to_range_list(self.old_page_text)
        new_ranges = page_text_to_range_list(self.page_text)
        removed_cnt = 0
        added_cnt = 0
        rmv_by = {}
        for r in old_ranges:
            if r not in new_ranges:
                removed_cnt += 1
                new_blocks = [x for x in report_data['coloranges'] if self.get_block_target(x) == r]
                if new_blocks:
                    x = new_blocks[0]
                    if x['by'] in rmv_by:
                        rmv_by[x['by']] += 1
                    else:
                        rmv_by[x['by']] = 1
        for r in new_ranges:
            if r not in old_ranges:
                added_cnt += 1

        summary = "Automatic update: "
        if added_cnt:
            summary += f"added {added_cnt}, "
        if removed_cnt:
            summary += f"removed {removed_cnt} ("
            user_entries = []
            remove_count = 0
            for k, v in sorted(rmv_by.items(), key=lambda x:x[1], reverse=True):
                user_entries.append(f"{v} blocked by {k}")
                remove_count += v
            if remove_count < removed_cnt:
                user_entries.append(f"{removed_cnt-remove_count} expired")
            summary += ", ".join(user_entries)
            summary += ")"

        self.edit_summary = summary


if __name__ == '__main__':
    report = rbesReport()
    report.run()
