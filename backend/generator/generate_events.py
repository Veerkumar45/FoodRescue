"""Generate reproducible synthetic sales events and submit them in micro-batches."""
import argparse, json, random, uuid
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

PRODUCTS=["PROD_001","PROD_002","PROD_003","PROD_004","PROD_005"]

def make_events(count, seed=42):
    random.seed(seed)
    now=datetime.now(timezone.utc)
    events=[]
    for i in range(count):
        ts=now-timedelta(minutes=random.randint(0,180))
        events.append({"event_id":f"GEN_{seed}_{i:07d}","event_type":"sale",
                       "product_id":random.choice(PRODUCTS),"quantity":random.randint(1,2),
                       "event_timestamp":ts.isoformat(),
                       "ingestion_timestamp":(ts+timedelta(seconds=random.randint(1,500))).isoformat()})
    return events

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--count",type=int,default=100)
    ap.add_argument("--batch-size",type=int,default=25)
    ap.add_argument("--url",default="http://127.0.0.1:8000/api/pipeline/process")
    ap.add_argument("--seed",type=int,default=42)
    args=ap.parse_args()
    events=make_events(args.count,args.seed)
    for start in range(0,len(events),args.batch_size):
        batch=events[start:start+args.batch_size]
        req=Request(args.url,data=json.dumps(batch).encode(),headers={"Content-Type":"application/json"},method="POST")
        try:
            with urlopen(req,timeout=30) as response:
                print(json.dumps(json.loads(response.read()),indent=2))
        except URLError as exc:
            print(f"Batch starting at {start} failed: {exc}")
            raise SystemExit(1)
if __name__=="__main__": main()
