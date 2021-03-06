from datetime import datetime, timedelta
import pywikibot
import pytz
import re
import sys


def parse_mw_ts(timestamp):
    time = datetime.strptime(str(timestamp), '%Y-%m-%dT%H:%M:%SZ')
    return pytz.utc.localize(time)

allowed_to_run = False
taking_over_clerking = False
first_overdue_case_edit = None
latest_case_edit = None
update_due = False

site = pywikibot.Site()
site.login()

output_page = pywikibot.Page(site, 'Wikipedia:Sockpuppet investigations/Cases/Overview')
latest_rev = output_page.latest_revision
latest_bot_edit = parse_mw_ts(latest_rev['timestamp'])
if latest_rev['user'] == 'ST47Bot':
    allowed_to_run = True
elif latest_bot_edit < (datetime.now(pytz.utc) - timedelta(minutes=30)):
    print("Last edit more than 30 minutes ago, continuing...")
else:
    print("Another user has edited the page!")
    sys.exit()


checkusers = list(site.allusers(group='checkuser'))
clerk_page = pywikibot.Page(site, 'Wikipedia:Sockpuppet investigations/SPI/Clerks').text
clerks = re.findall('\{\{user6b\|(.+?)\}\}', clerk_page, re.I)
cu_clerk_names = [*clerks, *[x['name'] for x in checkusers]]

casecategory = pywikibot.Category(site, 'Category:Open SPI cases')
case_pages = [x for x in site.categorymembers(casecategory) if x.namespace() == 4]

caselist = []
for case_page in case_pages:
    case = {}
    case['page'] = case_page
    case['casename'] = case_page.title().split('/')[-1]
    case['text'] = case_page.text
    timestamps = re.findall('\d\d:\d\d, \d\d? (?:January|February|March|April|May|June|July|August|September|October|November|December) \d{4} \(UTC\)', case['text'])
    timestamps = [pytz.utc.localize(datetime.strptime(x, '%H:%M, %d %B %Y (UTC)')) for x in timestamps]
    case['filed'] = min(timestamps)
    case['revisions'] = list(case_page.revisions())
    case['latest_rev'] = case['revisions'][0]
    case['latest_rev_ts'] = parse_mw_ts(case['revisions'][0]['timestamp'])
    if case['latest_rev_ts'] and case['latest_rev_ts'] > latest_bot_edit:
        update_due = True
        if first_overdue_case_edit is None or case['latest_rev_ts'] < first_overdue_case_edit:
            first_overdue_case_edit = case['latest_rev_ts']
        if latest_case_edit is None or case['latest_rev_ts'] > latest_case_edit:
            latest_case_edit = case['latest_rev_ts']

    if latest_case_edit is None or case['latest_rev_ts'] > latest_case_edit:
        latest_case_edit = case['latest_rev_ts']
    try:
        latest_cu_edit = [x for x in case['revisions'] if x['user'] in cu_clerk_names][0]
        latest_cu_edit_ts = parse_mw_ts(latest_cu_edit['timestamp'])
        if latest_cu_edit_ts >= case['filed']:
            case['latest_cu_edit'] = [x for x in case['revisions'] if x['user'] in cu_clerk_names][0]
            case['latest_cu_edit_ts'] = parse_mw_ts(case['latest_cu_edit']['timestamp'])
        else:
            case['latest_cu_edit'] = None
    except IndexError:
        case['latest_cu_edit'] = None
    def has_case_status(text, status):
        return re.search('\{\{SPI case status\|('+status+')\}\}', text, re.I)

    if has_case_status(case['text'], 'endorsed?'):
        case['status'] = 'endorse'
        case['order'] = 1
    elif has_case_status(case['text'], 'inprogress|checking'):
        case['status'] = 'inprogress'
        case['order'] = 2
    elif has_case_status(case['text'], 'relist(ed)?'):
        case['status'] = 'relist'
        case['order'] = 3
    elif has_case_status(case['text'], 'cu|checkuser|curequest|request'):
        case['status'] = 'CUrequest'
        case['order'] = 4
    elif has_case_status(case['text'], 'cudeclined?'):
        case['status'] = 'CUdeclined'
        case['order'] = 7
    elif has_case_status(case['text'], 'declined?'):
        case['status'] = 'declined'
        case['order'] = 8
    elif has_case_status(case['text'], 'cumoreinfo'):
        case['status'] = 'cumoreinfo'
        case['order'] = 9
    elif has_case_status(case['text'], 'moreinfo'):
        case['status'] = 'moreinfo'
        case['order'] = 10
    elif has_case_status(case['text'], 'clerk'):
        case['status'] = 'clerk'
        case['order'] = 11
    elif has_case_status(case['text'], 'admin'):
        case['status'] = 'admin'
        case['order'] = 12
    elif has_case_status(case['text'], 'open|'):
        case['status'] = 'open'
        case['order'] = 6
    elif has_case_status(case['text'], 'checked|completed'):
        case['status'] = 'checked'
        case['order'] = 5
    elif has_case_status(case['text'], 'hold'):
        case['status'] = 'hold'
        case['order'] = 13
    elif has_case_status(case['text'], 'cuhold'):
        case['status'] = 'CUhold'
        case['order'] = 14
    elif has_case_status(case['text'], 'closed?'):
        case['status'] = 'close'
        case['order'] = 15
    else:
        case['status'] = 'error'
        case['order'] = 16

    caselist.append(case)

if not allowed_to_run and\
   update_due and\
   first_overdue_case_edit > (latest_bot_edit + timedelta(minutes=30)):
    print("Update is more than 30 minutes overdue, bot taking over clerk responsibilities.")
    allowed_to_run = True
    taking_over_clerking = True

if not update_due:
    print("Update is not required, exiting.")
    sys.exit()

if not allowed_to_run:
    print("Bot is still not allowed to run, exiting.")
    sys.exit()

page_text  = "<!-- This bot (ST47Bot) has taken over clerking because an update to this page was more than 30 minutes overdue. It will stop clerking as soon as any other user edits this page.  -->\n"
page_text += "{{SPIstatusheader}}\n"
for case in sorted(caselist, key=lambda x:(x['order'], x['filed'])):
    def ftime(time):
        return time.strftime('%Y-%m-%d %H:%M')
    page_text += "{{"+f"SPIstatusentry|{case['casename']}|{case['status']}|{ftime(case['filed'])}"\
                 f"|{case['latest_rev']['user']}|{ftime(case['latest_rev_ts'])}"
    if case['latest_cu_edit']:
        page_text += f"|{case['latest_cu_edit']['user']}|{ftime(case['latest_cu_edit_ts'])}"
    else:
        page_text += "||"
    page_text += "}}\n"
page_text += "|}\n"

output_page = pywikibot.Page(site, 'Wikipedia:Sockpuppet investigations/Cases/Overview')
latest_rev = output_page.latest_revision
latest_bot_edit = parse_mw_ts(latest_rev['timestamp'])
if not taking_over_clerking and latest_rev['user'] != 'ST47Bot':
    print("Another user has edited the page!")
    sys.exit()
output_page = pywikibot.Page(site, 'User:ST47/spiclerk') ## TEMP
output_page.text = page_text
output_page.save(summary=f"Bot clerking SPI case list ({len(caselist)} open cases)", minor=True)
