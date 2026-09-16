#!/usr/bin/env python3
"""Fetch Trip.com hotel page (CNY) and extract JSON-LD rating + from-price.
Usage: trip_price.py HOTEL_ID [--in YYYY-MM-DD --out YYYY-MM-DD] [ids...]
"""
import re,subprocess,json,sys,os,time,concurrent.futures as cf
HERE=os.path.dirname(os.path.abspath(__file__))
CACHE=os.path.normpath(os.path.join(HERE,"..","research","_raw","cache","trip"))
os.makedirs(CACHE,exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"

def fetch(hid, ci, co):
    key=f"{hid}_{ci}_{co}"
    cf_=os.path.join(CACHE,key+".html")
    if os.path.exists(cf_) and os.path.getsize(cf_)>50000:
        return open(cf_,encoding="utf-8",errors="ignore").read()
    url=f"https://www.trip.com/hotels/nantong-hotel-detail-{hid}/?curr=CNY&checkIn={ci}&checkOut={co}"
    raw=subprocess.run(["curl","-sS","-m","40","-L","-A",UA,"-H","Accept-Language: zh-CN,zh;q=0.9",
        "-H","Cookie: curr=CNY; clientid=nantongguide; _ga=1",url],capture_output=True).stdout
    t=raw.decode("utf-8","ignore")
    open(cf_,"w",encoding="utf-8").write(t)
    return t

def parse(t):
    d={}
    m=re.search(r'priceRange\\+"\s*:\s*\\+"([^\\"]+)', t)
    if not m: m=re.search(r'priceRange[^:]{0,10}:\s*"([^"]+)"', t)
    d["price_from"]=m.group(1) if m else None
    m=re.search(r'reviewCount\\+"\s*:\s*\\+"(\d+)', t)
    d["reviews"]=m.group(1) if m else None
    m=re.search(r'ratingValue\\+"\s*:\s*\\+"([0-9.]+)', t)
    d["rating10"]=m.group(1) if m else None
    m=re.search(r'name\\+"\s*:\s*\\+"([^\\"]{2,60})', t)
    d["name"]=m.group(1) if m else None
    # also date-visible price list
    prices=re.findall(r'CNY\s?([0-9][0-9,]{1,6})', t)
    d["cny_seen"]=sorted(set(int(p.replace(",","")) for p in prices if p.replace(",","").isdigit() and 50<=int(p.replace(",",""))<=9999))[:12]
    return d

args=sys.argv[1:]
ci,co="2026-09-21","2026-09-22"
if "--in" in args:
    i=args.index("--in"); ci=args[i+1]; args=args[:i]+args[i+2:]
if "--out" in args:
    i=args.index("--out"); co=args[i+1]; args=args[:i]+args[i+2:]
res={}
with cf.ThreadPoolExecutor(max_workers=5) as ex:
    fut={ex.submit(fetch,h,ci,co):h for h in args}
    for f in cf.as_completed(fut):
        h=fut[f]
        try: res[h]=parse(f.result())
        except Exception as e: res[h]={"error":str(e)}
        time.sleep(0.2)
print(json.dumps({"checkin":ci,"checkout":co,"hotels":res},ensure_ascii=False,indent=1))
