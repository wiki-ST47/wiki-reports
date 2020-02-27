from datetime import datetime, timedelta
import re
from basereport import BaseReport, UsesBlocksMixin

class sbpReport(UsesBlocksMixin, BaseReport):
    page_name = "User:ST47/non-cu_sock_blocks"

    def gather_data(self):
        report_data = super().gather_data()

        lcu = list(self.homesite.allusers(group='checkuser'))
        lcu_usernames = [x['name'] for x in lcu]

        blocklist = report_data['blocklist']
        threshold = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%D")
        interestingblocks = [
            x for x in blocklist
            if 'user' in x and 'userid' in x and x['userid']
            and x['by'] not in lcu_usernames
            and x['timestamp'] >= threshold
            and re.search('sock', x['reason'], flags=re.I)
            and not re.search('checkuser', x['reason'], flags=re.I)]

        report_data['blocks'] = interestingblocks
        rowlist = []
        for block in report_data['blocks']:
            contribs = list(self.homesite.usercontribs(user=block['user']))
            this_row = {
                'block': block,
                'contribs': len(contribs),
            }
            if len(contribs):
                this_row['firstedit'] = contribs[-1]['timestamp']
            rowlist.append(this_row)
        report_data['rowlist'] = rowlist

        return report_data

    def get_row_iterator(self, report_data):
        return sorted(report_data['rowlist'],
                      reverse=True,
                      key=lambda x:x['block']['timestamp'])

    columns = [
        {
            'header': "Username",
            'formatter': lambda self,row: "{{checkuser|"+row['block']['user']+"}}",
        }, {
            'header': "Blocked By",
            'formatter': lambda self,row: f"[[Special:Contributions/{row['block']['by']}|{row['block']['by']}]]",
        }, {
            'header': "Contribs",
            'css': "class='nowrap'",
            'formatter': lambda self,row: row['contribs'],
        }, {
            'header': "First Edit",
            'css': "class='nowrap'",
            'formatter': lambda self,row: row['firstedit'] if 'firstedit' in row else '',
        }, {
            'header': "Blocked At",
            'css': "class='nowrap'",
            'formatter': lambda self,row: row['block']['timestamp'],
        }, {
            'header': "Blocked Until",
            'css': "class='nowrap'",
            'formatter': lambda self,row: row['block']['expiry'],
        }, {
            'header': "Block Reason",
            'formatter': lambda self,row: self.format_block_reason(row['block']['reason']),

        }
    ]

if __name__ == '__main__':
    report = sbpReport()
    report.run()

