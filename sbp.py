import re
from basereport import BaseReport, UsesWhoisMixin, UsesBlocksMixin

class sbpReport(UsesWhoisMixin, UsesBlocksMixin, BaseReport):
    page_name = "User:ST47/softblocked_proxies"

    def gather_data(self):
        report_data = super().gather_data()

        ipblocklist = report_data['ipblocklist']
        interestingblocks = [
            x for x in ipblocklist
            if re.search('proxy|proxies|webhost', x['reason'], flags=re.I)
            and 'anononly' in x]

        for x in interestingblocks:
            x['asn'] = self.whois.get_asn(x['rangestart'])
            x['asnname'] = self.whois.get_name_by_ip(x['rangestart'])

        report_data['blocks'] = interestingblocks
        return report_data

    def get_row_iterator(self, report_data):
        return report_data['blocks']

    def format_asn(self, row):
        if row['asn']:
            return "[https://tools.wmflabs.org/isprangefinder/hint.php?type=asn&range="+str(row['asn'])+" ASN"+str(row['asn'])+"]<br>"+row['asnname']
        return ""

    columns = [
        {
            'header': "IP",
            'formatter': lambda self,row: "{{checkip|"+row['user']+"}}",
        }, {
            'header': "ASN",
            'formatter': format_asn,
        }, {
            'header': "Blocked By",
            'formatter': lambda self,row: f"[[Special:Contributions/{row['by']}|{row['by']}]]",
        }, {
            'header': "Blocked Until",
            'css': "class='nowrap'",
            'formatter': lambda self,row: row['expiry'],
        }, {
            'header': "Block Reason",
            'formatter': lambda self,row: self.format_block_reason(row['reason']),

        }, {
            'header': "Reblock",
            'css': "class='nowrap'",
            'formatter': lambda self,row: "[https://en.wikipedia.org/wiki/Special:Block/"+row['user']+"?wpHardBlock=1 BLOCK]",
        }
    ]

if __name__ == '__main__':
    report = sbpReport()
    report.run()
