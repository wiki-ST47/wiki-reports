import random
from rbes import rbesReport

class grbesReport(rbesReport):
    page_name = "User:ST47/global_rangeblocks_expiring_soon"

    def get_blocks(self):
        bggen = self.homesite._generator(
            self.pywikibot.data.api.ListGenerator,
            type_arg='globalblocks')
        bggen.request['bgprop'] = ['id', 'address', 'by', 'timestamp',
                                   'expiry', 'reason', 'range']
        return bggen

    def filter_ip_blocks(self, blocklist):
        return blocklist

    def filter_relevant_blocks(self, blocklist):
        return blocklist

    def build_block_links(self, user, reason):
        random.seed(user)
        res  = "[https://meta.wikimedia.org/wiki/Special:GlobalBlock/"+user+"?wpExpiry="+str(random.randint(10,14))+"%20months ~1 YEAR]<br>"
        res += "[https://meta.wikimedia.org/wiki/Special:GlobalBlock/"+user+"?wpExpiry="+str(random.randint(30,42))+"%20months ~3 YEARS]"
        return res

    def get_block_target(self, block):
        return block['address']

if __name__ == '__main__':
    report = grbesReport()
    report.run()
