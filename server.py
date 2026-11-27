#!/usr/bin/env python3
"""OFFICE / NEWS intranet server. Python 3.9+, standard library only."""
import argparse, concurrent.futures, datetime as dt, email.utils, hashlib, html, http.server, json, pathlib, re, threading, time, urllib.parse as u, urllib.request as req, xml.etree.ElementTree as ET
from collections import defaultdict, deque
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parent
CATS=['Technology','Artificial Intelligence','Science & Space','Business','World News','Innovation','Cybersecurity','Future of Work','Gaming & Entertainment']
MEDIA='{http://search.yahoo.com/mrss/}'; ATOM='{http://www.w3.org/2005/Atom}'; DC='{http://purl.org/dc/elements/1.1/}'; CONTENT='{http://purl.org/rss/1.0/modules/content/}'
DEFAULT={'brand':'OFFICE / NEWS','subtitle':'THE WORLD AT A GLANCE','timezone':'Europe/Bucharest','story_seconds':10,'transition_ms':450,'refresh_seconds':300,'accent':'#FFB80C','background':'#10151D'}
CACHE=ROOT/'cache.json'; CONFIG=ROOT/'settings.json'; LOCK=threading.Lock(); STATE={'mode':'waiting','items':[],'stale':True,'settings':DEFAULT}; HEALTH={}; UTC=dt.timezone.utc
class Text(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.skip=0;self.images=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag=='img':self.images.append(dict(attrs).get('src',''))
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,d):
        if not self.skip:self.parts.append(d)
def clean(s,n):
    p=Text();p.feed(s or '');v=re.sub(r'\s+',' ',html.unescape(' '.join(p.parts))).strip();return v if len(v)<=n else v[:n-1].rsplit(' ',1)[0]+'…'
def val(e,*keys):
    for k in keys:
        t=e.find(k)
        if t is not None:
            v=''.join(t.itertext()).strip()
            if v:return v
    return ''
def https(s):
    try:
        p=u.urlsplit(s or '');return p.scheme=='https' and bool(p.hostname) and not p.username and not p.password
    except ValueError:return False
def date(s):
    if not s:return None
    try:d=email.utils.parsedate_to_datetime(s)
    except (ValueError,TypeError,OverflowError):
        try:d=dt.datetime.fromisoformat(s.replace('Z','+00:00'))
        except (ValueError,TypeError):return None
    return d.replace(tzinfo=UTC) if d.tzinfo is None else d.astimezone(UTC)
def canonical(s):
    if not https(s):return ''
    p=u.urlsplit(s);q=u.urlencode([(k,v) for k,v in u.parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid','cmp','ref')]);return u.urlunsplit((p.scheme,p.netloc.lower(),p.path.rstrip('/'),q,''))
def feedkey(f):return hashlib.sha256((f['url']+'\n'+f['category']+'\n'+f['source']).encode()).hexdigest()[:20]
class HTTPSRedirect(req.HTTPRedirectHandler):
    def redirect_request(self,r,fp,code,msg,headers,newurl):
        if not https(newurl):raise ValueError('Non-HTTPS redirect rejected')
        return super().redirect_request(r,fp,code,msg,headers,newurl)
def fetch(f,limit,days):
    if not https(f['url']):raise ValueError('HTTPS feed required')
    request=req.Request(f['url'],headers={'User-Agent':'OfficeNewsSignage/2.0','Accept':'application/rss+xml, application/atom+xml, application/xml, text/xml'})
    with req.build_opener(HTTPSRedirect()).open(request,timeout=12) as r:data=r.read(3_000_001)
    return parse(data,f,limit,days)
def parse(data,f,limit=10,days=14):
    if len(data)>3_000_000 or b'\x00' in data or re.search(br'<!\s*(DOCTYPE|ENTITY)',data,re.I):raise ValueError('Unsupported feed size or XML declaration')
    root=ET.fromstring(data);rows=root.findall('./channel/item') or root.findall(ATOM+'entry') or root.findall('{http://purl.org/rss/1.0/}item');out=[];now=dt.datetime.now(UTC)
    for e in rows:
        title=clean(val(e,'title',ATOM+'title','{http://purl.org/rss/1.0/}title'),210)
        if not title:continue
        when=date(val(e,'pubDate',ATOM+'published',ATOM+'updated',DC+'date'))
        if when and (now-when).total_seconds()>days*86400:continue
        link=val(e,'link','{http://purl.org/rss/1.0/}link')
        if not link:
            link=next((x.get('href','') for x in e.findall(ATOM+'link') if x.get('rel','alternate')=='alternate'),'')
        link=canonical(link);desc=val(e,'description',ATOM+'summary',ATOM+'content',CONTENT+'encoded','{http://purl.org/rss/1.0/}description');im='';credit=''
        if f.get('include_images'):
            candidates=e.findall('.//'+MEDIA+'content')+e.findall('.//'+MEDIA+'thumbnail')+e.findall('enclosure')+e.findall(ATOM+'link')
            good=[]
            for m in candidates:
                url=m.get('url') or m.get('href','');typ=m.get('type','');medium=m.get('medium','image')
                if https(url) and medium=='image' and (not typ or typ.startswith('image/')) and (m.tag not in ('enclosure',ATOM+'link') or typ.startswith('image/')):
                    try:w=int(m.get('width','0'))
                    except ValueError:w=0
                    good.append((w,url,clean(val(m,MEDIA+'credit') or val(e,MEDIA+'credit'),140)))
            if good:_,im,credit=max(good,key=lambda a:a[0])
            else:
                p=Text();p.feed(desc);im=next((x for x in p.images if https(x)),'')
        key=link or re.sub(r'\W+','',title.casefold());out.append({'id':hashlib.sha256(key.encode()).hexdigest()[:20],'title':title,'category':f['category'],'source':f['source'],'date':when.isoformat() if when else '', 'description':clean(desc,240) if f.get('include_description') else '', 'image':im,'credit':credit,'link':link})
    out.sort(key=lambda t:t['date'],reverse=True);return out[:limit]
def round_robin(groups,limit):
    buckets=defaultdict(list)
    for rows in groups:
        for t in rows:buckets[t['category']].append(t)
    qs={c:deque(sorted(buckets[c],key=lambda t:t['date'],reverse=True)) for c in CATS};seen_id=set();seen_title=set();counts=defaultdict(int);out=[]
    while any(qs.values()):
        for c,q in qs.items():
            if counts[c]>=limit:q.clear();continue
            while q:
                t=q.popleft();title=re.sub(r'\W+','',t['title'].casefold())
                if t['id'] in seen_id or title in seen_title:continue
                seen_id.add(t['id']);seen_title.add(title);counts[c]+=1;out.append(t);break
    return out
def read_cache():
    try:return json.loads(CACHE.read_text(encoding='utf-8'))
    except (OSError,ValueError):return {}
def save_cache(p):
    tmp=CACHE.with_suffix('.tmp');tmp.write_text(json.dumps(p,ensure_ascii=False),encoding='utf-8');tmp.replace(CACHE)
def cycle():
    global STATE,HEALTH
    cfg=json.loads(CONFIG.read_text(encoding='utf-8'));settings={k:cfg.get(k,v) for k,v in DEFAULT.items()};delay=max(60,min(3600,int(settings['refresh_seconds'])));settings['refresh_seconds']=delay;limit=max(1,min(5,int(cfg.get('max_per_topic',3))));days=max(1,min(90,int(cfg.get('max_age_days',14))));feeds=[f for f in cfg.get('feeds',[]) if f.get('enabled')]
    if any(f.get('category') not in CATS or not f.get('source') or not https(f.get('url')) for f in feeds):raise ValueError('Invalid enabled feed: check category, source and HTTPS URL')
    previous=read_cache();old=previous.get('feeds',{});current={};health={};errors=0;success=0
    def work(f):return fetch(f,limit*3,days)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        jobs={pool.submit(work,f):f for f in feeds}
        for future in concurrent.futures.as_completed(jobs):
            f=jobs[future];k=feedkey(f)
            try:
                rows=future.result()
                if not rows:raise ValueError('No eligible items')
                current[k]={'items':rows,'updated':dt.datetime.now(UTC).isoformat()};health[k]={'source':f['source'],'category':f['category'],'status':'ok','items':len(rows)};success+=1
            except Exception as e:
                errors+=1;entry=old.get(k,{});rows=entry.get('items',[])
                # Respect rights changes even when cached.
                rows=[dict(t,description=t['description'] if f.get('include_description') else '',image=t['image'] if f.get('include_images') else '',credit=t['credit'] if f.get('include_images') else '') for t in rows]
                if rows:current[k]={'items':rows,'updated':entry.get('updated','')}
                health[k]={'source':f['source'],'category':f['category'],'status':'cached' if rows else 'error','error':str(e)[:250]};print('Feed issue:',f['source'],f['category'],str(e),flush=True)
    items=round_robin([current.get(feedkey(f),{}).get('items',[]) for f in feeds],limit);updated=max((x.get('updated','') for x in current.values()),default='');p={'mode':'live' if items else ('waiting' if feeds else 'demo'),'items':items,'updated':updated,'stale':bool(errors),'settings':settings}
    save_cache({'feeds':current,'payload':p});
    with LOCK:STATE=p;HEALTH=health
    return delay
def worker():
    global STATE
    while True:
        started=time.monotonic();delay=300
        try:delay=cycle()
        except Exception as e:
            print('Refresh error:',e,flush=True)
            with LOCK:STATE=dict(STATE,stale=True)
        time.sleep(max(1,delay-(time.monotonic()-started)))
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path=u.urlsplit(self.path).path
        if path in ('/','/index.html'):data=(ROOT/'index.html').read_bytes();typ='text/html; charset=utf-8'
        elif path in ('/news.json','/health.json'):
            with LOCK:p=STATE if path=='/news.json' else {'mode':STATE['mode'],'stale':STATE['stale'],'items':len(STATE['items']),'updated':STATE.get('updated',''),'feeds':list(HEALTH.values())};data=json.dumps(p,ensure_ascii=False).encode();typ='application/json; charset=utf-8'
        else:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass
    def log_message(self,fmt,*args):pass
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--host',default='127.0.0.1');ap.add_argument('--port',type=int,default=8080);a=ap.parse_args()
    threading.Thread(target=worker,daemon=True).start();print('OFFICE / NEWS http://%s:%s/'%(a.host,a.port),flush=True);http.server.ThreadingHTTPServer((a.host,a.port),Handler).serve_forever()
