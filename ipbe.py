from urllib.parse import quote_plus
from basereport import BaseReport, UsesWhoisMixin, UsesBlocksMixin


class ipbeReport(UsesBlocksMixin, UsesWhoisMixin, BaseReport):
    page_name = "User:ST47/ip_block_exemptions"

    def gather_data(self):
        report_data = super().gather_data()

        blocklist = report_data['blocklist']

        lipbe = list(self.homesite.allusers(group='ipblock-exempt'))
        gipbegen = self.homesite._generator(
            self.pywikibot.data.api.ListGenerator,
            type_arg='globalallusers')
        gipbegen.request['agugroup'] = 'global-ipblock-exempt'
        gipbegen.request['aguprop'] = 'lockinfo|groups|existslocally'
        gipbe = list(gipbegen)

        lipbe_usernames = [x['name'] for x in lipbe]
        gipbe_need_local = [x['name'] for x in gipbe
                            if x['name'] not in lipbe_usernames
                            and 'existslocally' in x]

        need_local_usernames = [*lipbe_usernames, *gipbe_need_local]
        user_list = []
        for i in range(0,(len(need_local_usernames)-1)//500+1):
            gen = self.homesite.users(need_local_usernames[(i*500):((i+1)*500)])
            gen.request['usprop'].append('groupmemberships')
            user_list.extend(gen)

        for user in user_list:
            if 'ipblock-exempt' in user['groups']:
                user['lipbe'] = True
            gipbe_user = [x for x in gipbe if user['name'] == x['name']]
            if gipbe_user:
                user['gipbe'] = gipbe_user
            block_user = [x for x in blocklist if 'user' in x and  user['name'] == x['user']]
            if block_user:
                user['block'] = block_user
            if user['editcount']:
                contribs = list(self.homesite.usercontribs(user=user['name'], total=100))
                if contribs:
                    user['contribs'] = contribs
                    user['latest'] = contribs[0]
                    user['earliest'] = contribs[-1]
            blocklog = list(self.homesite.logevents(page="User:"+user['name'], logtype='block'))
            if blocklog:
                user['blocklog'] = blocklog
            ipbe = [x for x in user['groupmemberships'] if x['group'] == 'ipblock-exempt']
            if ipbe:
                user['lipbe'] = ipbe[0]


        user_list = [x for x in user_list
                     if 'lipbe' in x or 'block' in x or 'blocklog' in x or
                     ('latest' in x and x['latest']['timestamp'] > '2017')]
        user_list = [x for x in user_list if 'groups' not in x or 'sysop' not in x['groups']]

        report_data['user_list'] = user_list
        return report_data

    def format_blocklog(self, row):
        if 'blocklog' in row:
            return f"[https://en.wikipedia.org/w/index.php?title=Special:Log/block&page=User:{quote_plus(row['name'])} {len(row['blocklog'])} entries]"
        return ""

    columns = [
        {
            'header': "Username",
            'formatter': lambda self,row:"{{checkuser|"+row['name']+"}}",
        }, {
            'header': "LIPBE",
            'formatter': lambda self,row:row['lipbe']['expiry'] if 'lipbe' in row else "",
        }, {
            'header': "GIPBE",
            'formatter': lambda self,row:"True" if 'gipbe' in row else "",
        }, {
            'header': "Blocked",
            'formatter': lambda self,row:"True" if 'block' in row else "",
        }, {
            'header': "Blocklog",
            'formatter': format_blocklog,
        }, {
            'header': "Editcount",
            'formatter': lambda self,row:row['editcount'] if 'editcount' in row else "",
        }, {
            'header': "Last Edit",
            'formatter': lambda self,row:row['latest']['timestamp'] if 'contribs' in row else "",
        }
    ]

    def get_row_iterator(self, report_data):
        return report_data['user_list']


if __name__ == '__main__':
    report = ipbeReport()
    report.run()
