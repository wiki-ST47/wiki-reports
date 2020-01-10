from urllib.parse import quote_plus
from basereport import BaseReport, UsesBlocksMixin, TwoLevelTableMixin

class osv6rReport(TwoLevelTableMixin, UsesBlocksMixin, BaseReport):
    page_name = "User:ST47/overspecific_v6_blocks"

    def filter_range_blocks(self, blocklist):
        return blocklist

    def filter_relevant_blocks(self, blocklist):
        for x in blocklist:
            x['iprange'] = self.ipaddress.ip_network(x['user'])
        return [x for x in blocklist if x['iprange'].version == 6]

    def network_to_mw_prefix(self, network):
        return ':'.join(map(lambda x:x if x else '0', str(network).split(':')[0:4])).upper()+':'

    def gather_data(self):
        site = self.homesite
        report_data = super().gather_data()
        ip6blocklist = report_data['filteredranges']

        ip6directblocks = {}
        for block in ip6blocklist:
            if block['iprange'].prefixlen > 64:
                prefix = block['iprange'].supernet(new_prefix=64)
                if prefix not in ip6directblocks:
                    ip6directblocks[prefix] = []
                ip6directblocks[prefix].append(block)

        for block in ip6blocklist:
            if block['iprange'].prefixlen <= 64:
                ip6directblocks = {k:v for (k,v) in ip6directblocks.items()
                                   if not block['iprange'].supernet_of(k)}

        info_rows = []
        for prefix, data in ip6directblocks.items():
            fb = min([x['timestamp'] for x in data])
            csfb = len(list(site.usercontribs(userprefix=self.network_to_mw_prefix(prefix), start=fb, reverse=True)))
            cslb = None
            if len(data) > 1:
                lb = max([x['timestamp'] for x in data])
                cslb = len(list(site.usercontribs(userprefix=self.network_to_mw_prefix(prefix), start=lb, reverse=True)))
            if cslb == 0 or (csfb == 0 and cslb is None):
                continue
            info_rows.append({
                'prefix': prefix,
                'data': data,
                'csfb': csfb,
                'cslb': cslb,
            })

        report_data['info_rows'] = info_rows
        return report_data

    def format_iprange(self, row, subrow):
        res  = "{{checkip|"+str(row['prefix'])+"}}<br>\n"
        res += f"{row['csfb']} contribs since first block<br>"
        if len(row['data']) > 1:
            res += f"\n{row['cslb']} contribs since last block<br>"
        return res

    def format_reblock(self, row, subrow):
        reason = f"Widening block by [[User:{subrow['by']}]] on [[Special:Contributions/{subrow['user']}]] due to ongoing disruption. Original block was for: {subrow['reason']}"
        return f"[https://en.wikipedia.org/wiki/Special:Block/{row['prefix']}?wpExpiry={quote_plus(subrow['expiry'])}&wpReason=other&wpReason-other={quote_plus(reason)} RE-BLOCK]"

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
            'header': "Blocked From",
            'css': "class='nowrap'",
            'formatter': lambda self,row,subrow: subrow['timestamp'],
        }, {
            'header': "Blocked Until",
            'css': "class='nowrap'",
            'formatter': lambda self,row,subrow: subrow['expiry'],
        }, {
            'header': "Block Reason",
            'formatter': lambda self,row,subrow: f"{self.format_block_reason(subrow['reason'])}",
        }, {
            'header': "Reblock",
            'formatter': format_reblock,
        }
    ]

    def get_row_iterator(self, report_data):
        return sorted(report_data['info_rows'],
                      reverse=True,
                      key=lambda x:max([y['timestamp'] for y in x['data']]))

    def get_subrow_iterator(self, row):
        return sorted(row['data'], reverse=True, key=lambda x:x['timestamp'])


if __name__ == '__main__':
    report = osv6rReport()
    report.run()
