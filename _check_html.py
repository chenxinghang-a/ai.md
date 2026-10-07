import json, requests, re

cookies = {}
for c in json.load(open(r'C:/Users/cxx/WorkBuddy/Claw/.browser_cookies.json')):
    cookies[c['name']] = c['value']

url = 'http://www.gaoxiaokaoshi.com/Study/LibraryStudyList.aspx'
resp = requests.get(url, cookies=cookies, timeout=15)
print(f'Status: {resp.status_code}')

# 找所有参加练习相关的HTML
matches = re.findall(r'参加练习.{0,100}', resp.text)
for m in matches[:20]:
    print(f'  {m}')
