#!/usr/bin/env python3
"""Read-only Fanqie long-form income probe.

Uses the site's own book switcher and reloads the selected income view so Fanqie
itself generates valid signed GET requests. No writes are performed and no
comment/message/chapter body text is collected.
"""
from __future__ import annotations
import argparse, asyncio, importlib.util, json, math, re
from pathlib import Path
from urllib.parse import urlparse
import fanqie_probe

BASE="https://fanqienovel.com"; BOOK_MANAGE=BASE+"/main/writer/book-manage"
INCOME_PATHS=("/api/author/income/book_summary_v3/v0/","/api/author/income/book_daily_v3/v0/")

class ProbeError(RuntimeError): pass

def load_runtime(d:Path):
    s=d/"fanqie_upload.py"; spec=importlib.util.spec_from_file_location("fanqie_runtime_income_probe",s)
    if spec is None or spec.loader is None: raise ProbeError(f"cannot load runtime: {s}")
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def bid(p:Path):
    x=json.loads((p/"platform-sync"/"config.json").read_text(encoding="utf-8")); v=str(x.get("book_id") or "").strip()
    if not v: raise ProbeError(f"missing book_id: {p}")
    return v

def num(v):
    if isinstance(v,bool): return None
    if isinstance(v,(int,float)) and math.isfinite(float(v)): return v
    if isinstance(v,str):
        s=v.replace(",","").strip()
        if re.fullmatch(r"-?\d+(?:\.\d+)?%?",s):
            try:
                n=float(s[:-1] if s.endswith("%") else s); return n/100 if s.endswith("%") else n
            except ValueError: pass
    return None

HINT=("read","reader","follow","pursue","completion","shelf","remind","comment","income","amount","fee","revenue","earning","reward","gift","pay","count","rate","total","daily","monthly","yesterday","today","novel","audio")
BLOCK=("content","reply","message","nickname","phone","email","address","intro","summary")
def metrics(v,prefix="",out=None,limit=500):
    out={} if out is None else out
    if len(out)>=limit:return out
    if isinstance(v,dict):
        for k,c in v.items():
            p=f"{prefix}.{k}" if prefix else str(k)
            if any(x in p.lower() for x in BLOCK):continue
            metrics(c,p,out,limit)
    elif isinstance(v,list):
        for i,c in enumerate(v[:30]):metrics(c,f"{prefix}[{i}]",out,limit)
    elif any(x in prefix.lower() for x in HINT):
        n=num(v)
        if n is not None:out[prefix]=n
    return out

def unwrap(b):return b.get("data") if isinstance(b,dict) and "data" in b else b
def summary_body(body,status=200):
    data=unwrap(body);keys=sorted(map(str,data.keys()))[:220] if isinstance(data,dict) else []
    out={"http_status":status,"keys":keys,"metrics":metrics(data)}
    if isinstance(body,dict):out["code"]=body.get("code");out["message"]=body.get("message")
    return out

async def get_json(page,path,query):
    return await page.evaluate("""async ({path,query})=>{const u=new URL(path,location.origin);for(const[k,v]of Object.entries(query||{}))u.searchParams.set(k,String(v));const r=await fetch(u.toString(),{credentials:'include'});const t=await r.text();let b=null;try{b=JSON.parse(t)}catch(_){};return{status:r.status,body:b};}""",{"path":path,"query":query})
async def click_exact(page,text):
    loc=page.get_by_text(text,exact=True)
    for i in range(min(await loc.count(),30)):
        el=loc.nth(i)
        try:
            if await el.is_visible():await el.click(timeout=5000);await page.wait_for_timeout(1600);return True
        except Exception:continue
    return False
async def ui_income_segment(page):
    lines=[x.strip() for x in (await page.locator("body").inner_text()).splitlines() if x.strip() and len(x.strip())<=120]
    out=[];anchors=("收益概览","昨日番茄收益","累计番茄收益","收益趋势","阅读收益","听书收益","互动收益","每日收益","每月稿费")
    for i,line in enumerate(lines):
        if any(a in line for a in anchors):
            for item in lines[max(0,i-1):min(len(lines),i+4)]:
                if item not in out:out.append(item)
        if len(out)>=80:break
    return out

async def run(novel_dirs,runtime_arg):
    rd=fanqie_probe.resolve_runtime(runtime_arg);rt=load_runtime(rd);rt.load_config();books=[(p.name,bid(p)) for p in novel_dirs]
    async with rt.async_playwright() as pw:
        browser,context=await rt.create_context(pw,headless=True);page=await context.new_page();current=None;captured={s:{} for s,_ in books};tasks=set()
        async def capture(resp):
            nonlocal current
            try:
                parsed=urlparse(resp.url)
                if current is None or resp.request.method.upper()!="GET" or parsed.path not in INCOME_PATHS:return
                if "json" not in (resp.headers.get("content-type") or "").lower():return
                captured[current][parsed.path]=summary_body(await resp.json(),resp.status)
            except Exception:return
        def on_response(resp):
            t=asyncio.create_task(capture(resp));tasks.add(t);t.add_done_callback(tasks.discard)
        page.on("response",on_response)
        try:
            if not await rt.goto_with_login_retry(page,BOOK_MANAGE):raise ProbeError("cannot open writer dashboard")
            await rt.settle_page(page)
            bl=await get_json(page,"/api/author/book/book_list/v0",{"page_index":0,"page_count":50});data=unwrap(bl.get("body"));rows=data.get("book_list",[]) if isinstance(data,dict) else []
            names={str(x.get("book_id")):str(x.get("book_name") or "") for x in rows if isinstance(x,dict)}
            report={"books":{s:{"book_id":b,"income":{},"income_ui_segment":[],"switch_success":False} for s,b in books}}
            for slug,book_id in books:
                await rt.goto_with_login_retry(page,BOOK_MANAGE);await page.wait_for_timeout(700)
                if not await click_exact(page,"小说收益"):continue
                name=names.get(book_id,"")
                if not name or not await click_exact(page,"切换作品"):continue
                switched=await click_exact(page,name);report["books"][slug]["switch_success"]=switched
                if not switched:continue
                current=slug
                await page.reload(wait_until="domcontentloaded",timeout=30000);await page.wait_for_timeout(4200)
                report["books"][slug]["income_ui_segment"]=await ui_income_segment(page)
                current=None
            if tasks:await asyncio.gather(*list(tasks),return_exceptions=True)
            for slug,_ in books:report["books"][slug]["income"]=captured[slug]
            await rt.save_auth(context)
            print("FANQIE_DATA_PROBE_JSON_BEGIN");print(json.dumps(report,ensure_ascii=False,separators=(",",":"),default=str));print("FANQIE_DATA_PROBE_JSON_END");return 0
        finally:
            page.remove_listener("response",on_response);await rt.close_browser_safely(browser)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("novel_dirs",nargs="+",type=Path);ap.add_argument("--runtime");a=ap.parse_args()
    try:return asyncio.run(run([p.resolve() for p in a.novel_dirs],a.runtime))
    except (fanqie_probe.ProbeError,ProbeError,RuntimeError,OSError,json.JSONDecodeError) as e:print(f"ERROR: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
