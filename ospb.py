from urllib.parse import quote_plus
from basereport import BaseReport, UsesBlocksMixin, TwoLevelTableMixin

class ospbReport(UsesBlocksMixin, BaseReport):
    page_name = "User:ST47/overspecific_partial_blocks"

    def get_blocks(self):
        blockgen = super().get_blocks()
        blockgen.request['bkprop'].append('restrictions')
        return blockgen

    def filter_ip_blocks(self, blocklist):
        return blocklist

    def filter_range_blocks(self, blocklist):
        return blocklist

    def filter_relevant_blocks(self, blocklist):
        return [x for x in blocklist if 'partial' in x and 'user' in x]

    def network_to_mw_prefix(self, network):
        return ':'.join(map(lambda x:x if x else '0', str(network).split(':')[0:4])).upper()+':'

    def gather_data(self):
        site = self.homesite
        report_data = super().gather_data()
        partialblocklist = report_data['filteredranges']

        info_rows = []
        for block in partialblocklist:
            csb = len(list(site.usercontribs(user=block['user'], start=block['timestamp'], reverse=True)))
            info_rows.append({
                'block': block,
                'csb': csb,
            })

        report_data['info_rows'] = info_rows
        return report_data

    def format_target(self, row):
        res  = f"[[Special:Contributions/{row['block']['user']}|{row['block']['user']}]]<br>\n"
        res += f"{row['csb']} contribs since blocked<br>"
        return res

    def format_conditions(self, row):
        restrictions = row['block']['restrictions']
        if not restrictions:
            return "bgcolor='#FF0000' | None"
        data = "\n"
        for k,v in restrictions.items():
            data += f"* {k}\n"
            for i in v:
                if k == 'pages':
                    data += f"** [[{i['title']}]]\n"
                elif k == 'namespaces':
                    if i == 0:
                        data += f"** (article)\n"
                    else:
                        data += f"** {self.homesite.namespace(i)}\n"
        return data

    def format_reblock(self, row):
        reason = f"Widening block by [[User:{row['block']['by']}]] on [[Special:Contributions/{row['block']['user']}]] due to ongoing disruption. Original block was for: {row['block']['reason']}"
        return f"[https://en.wikipedia.org/wiki/Special:Block/{row['block']['user']}?wpExpiry={quote_plus(row['block']['expiry'])}&wpReason=other&wpReason-other={quote_plus(reason)} RE-BLOCK]"

    columns = [
        {
            'header': "Block Target",
            'formatter': format_target,
        }, {
            'header': "Blocked By",
            'formatter': lambda self,row: f"[[Special:Contributions/{row['block']['by']}|{row['block']['by']}]]",
        }, {
            'header': "Blocked From",
            'css': "class='nowrap'",
            'formatter': lambda self,row: row['block']['timestamp'],
        }, {
            'header': "Blocked Until",
            'css': "class='nowrap'",
            'formatter': lambda self,row: row['block']['expiry'],
        }, {
            'header': "Block Reason",
            'formatter': lambda self,row: f"{self.format_block_reason(row['block']['reason'])}",
        }, {
            'header': "Block Conditions",
            'formatter': format_conditions,
        }, {
            'header': "Reblock",
            'formatter': format_reblock,
        }
    ]

    def get_row_iterator(self, report_data):
        return sorted(report_data['info_rows'],
                      reverse=True,
                      key=lambda x:x['block']['timestamp'])


if __name__ == '__main__':
    report = ospbReport()
    report.run()
