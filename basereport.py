import pywikibot
from flare.tools.whoisip import WhoisLookup
import pyasn
from urllib.parse import quote_plus
from datetime import datetime, timedelta
import random
import re

class UsesWhoisMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.whois = WhoisLookup(
            'flaredata/ipasn.dat',
            'flaredata/asnames.txt',
        )

class BaseReport(object):
    homesite_kwargs = {}

    def __init__(self, *args, **kwargs):
        self.pywikibot = pywikibot
        self.homesite = self.pywikibot.Site(**self.homesite_kwargs)
        self.homesite.login()

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
