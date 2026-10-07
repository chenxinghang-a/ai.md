import json, sys
c = json.load(open(sys.argv[1]))
s = [x for x in c if x['name'] == 'ASP.NET_SessionId']
if s:
    print(f"ASP.NET_SessionId={s[0]['value']}")
