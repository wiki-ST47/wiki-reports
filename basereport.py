import ipaddress
import re

from flare.tools.whoisip import WhoisLookup
import pywikibot


class UsesWhoisMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whois = WhoisLookup(
            'flaredata/ipasn.dat',
            'flaredata/asnames.txt',
        )

class UsesBlocksMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ipaddress = ipaddress

    def get_blocks(self):
        return self.homesite.blocks()

    def filter_ip_blocks(self, blocklist):
        ipblocklist = [x for x in blocklist
                       if 'user' in x
                       and x['userid'] == 0
                       and x['rangestart'] != '0.0.0.0']
        self.ipblocklist = ipblocklist
        return ipblocklist

    def filter_range_blocks(self, blocklist):
        res = [x for x in blocklist if x['rangestart'] != x['rangeend']]
        return res

    def filter_relevant_blocks(self, blocklist):
        res = [x for x in blocklist
               if re.search('proxy|proxies|webhost', x['reason'], flags=re.I)]
        return res

    def is_currently_blocked(self, prefix):
        prefixobj = self.ipaddress.ip_network(prefix)
        return [x for x in self.ipblocklist
                if x['rangestart'] and x['rangestart'] != '0.0.0.0'
                and prefixobj.version == self.ipaddress.ip_network(x['user']).version
                and prefixobj.subnet_of(self.ipaddress.ip_network(x['user']))]

    def gather_data(self):
        report_data = super().gather_data()

        blockiter = self.get_blocks()
        blocklist = [x for x in blockiter]
        ipblocklist = self.filter_ip_blocks(blocklist)
        blockedranges = self.filter_range_blocks(ipblocklist)
        coloranges = self.filter_relevant_blocks(blockedranges)

        report_data['blocklist'] = blocklist
        report_data['ipblocklist'] = ipblocklist
        report_data['blockedranges'] = blockedranges
        report_data['coloranges'] = coloranges
        report_data['filteredranges'] = coloranges

        return report_data

    def format_block_reason(self, reason):
        return reason.replace("{{", "{{tl|")\
                     .replace("}}", "}}")\
                     .replace('<!--', '&lt;!--')\
                     .replace('-->', '--&gt;')


class TwoLevelTableMixin(object):
    def build_row(self, row):
        res = ""
        subrows = self.get_subrow_iterator(row)
        subrow_count = len(subrows)
        first_row = True
        for subrow in subrows:
            res += "|-\n"
            for column in self.columns:
                if 'grouped' in column and first_row:
                    res += self.build_cell(row, subrow, column, subrow_count)
                elif 'grouped' not in column:
                    res += self.build_cell(row, subrow, column)
            first_row = False
        return res

    def build_cell(self, row, subrow, column, rowspan=None):
        res = ""
        style = ""
        if 'css' in column:
            style = f"{column['css']} "
        if rowspan:
            style += f"rowspan='{rowspan}' "
        if style:
            res += f"| {style}"
        res += f"| {column['formatter'](self, row, subrow)}\n"
        return res


class BaseReport(object):
    homesite_kwargs = {}

    def __init__(self, *args, **kwargs):
        self.pywikibot = pywikibot
        self.homesite = self.pywikibot.Site(**self.homesite_kwargs)
        self.homesite.login()

    def gather_data(self):
        return {}

    def run(self):
        report_data = self.gather_data()
        self.get_report_page()
        self.build_report(report_data)
        self.submit_report()

    def submit_report(self):
        self.page.text = self.page_text
        self.page.save(summary=self.edit_summary, minor=True)

    def get_report_page(self):
        self.page = self.pywikibot.Page(self.homesite, self.page_name)
        self.old_page_text = self.page.text

    def build_cell(self, row, column):
        res = ""
        if 'css' in column:
            res += f"| {column['css']} "
        res += f"| {column['formatter'](self, row)}\n"
        return res

    def build_row(self, row):
        res = "|-\n"
        for column in self.columns:
            res += self.build_cell(row, column)
        return res

    def build_report(self, report_data):
        page_text = "{{/header}}\n"
        page_text += "{| class='wikitable sortable'\n"
        page_text += "|-\n"
        for column in self.columns:
            page_text += f"! {column['header']}\n"
        for row in self.get_row_iterator(report_data):
            page_text += self.build_row(row)
        page_text += "|}\n"
        self.page_text = page_text
        self.edit_summary = "Automatically updating report"
