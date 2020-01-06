import pywikibot
from flare.tools.whoisip import WhoisLookup
import pyasn
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import random
import re
from basereport import BaseReport, UsesWhoisMixin


class rbesReport(UsesWhoisMixin, BaseReport):
    page_name = "User:ST47/rangeblocks_expiring_soon"

    def get_blocks(self):
        return self.homesite.blocks()

    def filter_ip_blocks(self, blocklist):
        ipblocklist = [x for x in blocklist if 'user' in x and x['userid'] == 0]
        return ipblocklist

    def filter_range_blocks(self, blocklist):
        res = [x for x in blocklist if x['rangestart'] != x['rangeend']]
        return res

    def filter_relevant_blocks(self, blocklist):
        res = [x for x in blocklist
               if re.search('proxy|proxies|webhost', x['reason'], flags=re.I)]
        return res

    def gather_data(self):
        site = self.homesite
        report_data = {}

        blockiter = self.get_blocks()
        blocklist = [x for x in blockiter]
        ipblocklist = self.filter_ip_blocks(blocklist)
        blockedranges = self.filter_range_blocks(ipblocklist)
        coloranges = self.filter_relevant_blocks(blockedranges)

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

    def format_block_reason(self, reason):
        return reason.replace("{{", "{{tl|")\
                     .replace("}}", "}}")\
                     .replace('<!--', '&lt;!--')\
                     .replace('-->', '--&gt;')

    def build_block_links(self, user):
        random.seed(user)
        res  = "[https://en.wikipedia.org/wiki/Special:Block/"+user+"?wpExpiry="+str(random.randint(10,14))+"%20months&wpHardBlock=1 ~1 YEAR]<br>"
        res += "[https://en.wikipedia.org/wiki/Special:Block/"+user+"?wpExpiry="+str(random.randint(30,42))+"%20months&wpHardBlock=1 ~3 YEARS]"
        return res

    def build_report(self, report_data):
        page_text = "{{/header}}\n"
        page_text += "{| class='wikitable sortable'\n"
        page_text += "|-\n"
        page_text += "! IP Range\n"
        page_text += "! ASN\n"
        page_text += "! Blocked By\n"
        page_text += "! Blocked Until\n"
        page_text += "! Block Reason\n"
        page_text += "! Reblock\n"
        for block in report_data['expiringsoon']:
            target = self.get_block_target(block)
            page_text += "|-\n"
            page_text += "| {{checkip|"+target+"}}\n"
            if block['asn']:
                page_text += "| [https://tools.wmflabs.org/isprangefinder/hint.php?type=asn&range="+str(block['asn'])+" ASN"+str(block['asn'])+"]<br>"+block['asnname']+"\n"
            else:
                page_text += "| \n"
            page_text += f"| [[Special:Contributions/{block['by']}|{block['by']}]]\n"
            page_text += f"| class='nowrap' | {block['expiry']}\n"
            page_text += "| "+self.format_block_reason(block['reason'])+"\n"
            page_text += "| class='nowrap' | "+self.build_block_links(target)+"\n"
        page_text += "|}\n"

        def page_text_to_range_list(text):
            return [m for m in re.findall('\{\{checkip|([0-9a-f.:/]+)\}\}', text, re.I)]

        old_ranges = page_text_to_range_list(self.old_page_text)
        new_ranges = page_text_to_range_list(page_text)
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

        self.page_text = page_text
        self.edit_summary = summary


if __name__ == '__main__':
    report = rbesReport()
    report.run()
