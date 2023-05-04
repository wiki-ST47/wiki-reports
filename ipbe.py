from urllib.parse import quote_plus
from basereport import BaseReport, UsesWhoisMixin, UsesBlocksMixin


class ipbeReport(
        UsesBlocksMixin,
        UsesWhoisMixin,
        BaseReport):
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
#            glocklog = self.meta.logevents(page="User:"+user['name']+"@global")
#            glocklog.request['leaction'] = 'globalauth/lock'
#            glocklog = list(glocklog)
#            if glocklog:
#                user['glocklog'] = glocklog
            gpermlog = list(self.meta.logevents(page="User:"+user['name'], logtype='rights'))
            for wiki in ('enwiki', 'zhwiki'):
                gpermlog.extend(
                    list(self.meta.logevents(page="User:"+user['name']+"@"+wiki, logtype='rights'))
                )
            if gpermlog:
                user['gpermlog'] = gpermlog
            ipbe = [x for x in user['groupmemberships'] if x['group'] == 'ipblock-exempt']
            if ipbe:
                user['lipbe'] = ipbe[0]
            permlog = list(self.homesite.logevents(page="User:"+user['name'], logtype='rights'))
            for entry in permlog:
                if 'oldgroups' not in entry._params or 'newgroups' not in entry._params:
                    continue
                if 'ipblock-exempt' in entry._params['newgroups'] and\
                   'ipblock-exempt' not in entry._params['oldgroups']:
                    user['granter'] = entry.data['user']
                    user['grant-date'] = entry.data['timestamp']
                    break

        user_list = [x for x in user_list
                     if 'lipbe' in x or 'block' in x or 'blocklog' in x or
                     ('latest' in x and x['latest']['timestamp'] < '2019')]
        user_list = [x for x in user_list if 'groups' not in x or 'sysop' not in x['groups']]

        report_data['user_list'] = user_list
        return report_data

    def format_blocklog(self, row):
        if 'blocklog' in row:
            return f"[https://en.wikipedia.org/w/index.php?title=Special:Log/block&page=User:{quote_plus(row['name'])} {len(row['blocklog'])} entries]"
        return ""

    def format_glocklog(self, row):
        if 'glocklog' in row:
            return f"[https://meta.wikimedia.org/w/index.php?title=Special:Log/globalauth&page=User:{quote_plus(row['name'])}%40global {len(row['glocklog'])} entries]"
        return ""

    def format_gpermlog(self, row):
        if 'gpermlog' in row:
            return f"[https://meta.wikipedia.org/w/index.php?title=Special:Log/rights&page=User:{quote_plus(row['name'])}%40* {len(row['gpermlog'])} entries]"
        return ""

    def format_granter(self, row):
        if 'granter' in row:
            return f"[[User:{row['granter']}|{row['granter']}]]"
        return ""

    def format_grantdate(self, row):
        if 'grant-date' in row:
            return f"{row['grant-date']}"
        return ""


    columns = [
        {
            'header': "Username",
            'formatter': lambda self,row:"{{/ul|"+row['name']+"}}",
        }, {
            'header': "Links",
            'no_content': True,
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
#            'header': "Glocks",
#            'formatter': format_glocklog,
#        }, {
            'header': "GlobalRights",
            'formatter': format_gpermlog,
        }, {
            'header': "Editcount",
            'formatter': lambda self,row:row['editcount'] if 'editcount' in row else "",
        }, {
            'header': "Last Edit",
            'formatter': lambda self,row:row['latest']['timestamp'] if 'contribs' in row else "",
        }, {
            'header': "Granted By",
            'formatter': format_granter,
        }, {
            'header': "Granted",
            'formatter': format_grantdate,
        }
    ]

    def get_row_iterator(self, report_data):
        return report_data['user_list']


if __name__ == '__main__':
    report = ipbeReport()
    report.run()
