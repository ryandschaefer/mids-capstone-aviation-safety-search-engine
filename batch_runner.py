import argparse
import json
import os
import re
import time
from pathlib import Path

from openai import OpenAI


SHARD_RE = re.compile(r".*_shard_(\d+)\.jsonl$")


def shard_index(path):
    m = SHARD_RE.match(path.name)
    if not m:
        return -1
    return int(m.group(1))

def extract_output_text(obj):
    resp = obj.get("response") or obj.get("result") or {}
    if not isinstance(resp, dict):
        return None

    if isinstance(resp.get("output_text"), str) and resp["output_text"].strip():
        return resp["output_text"]

    out = resp.get("output")
    if isinstance(out, list):
        for item in out:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for c in content:
                    if not isinstance(c, dict):
                        continue
                    if isinstance(c.get("text"), str) and c["text"].strip():
                        return c["text"]
                    if isinstance(c.get("content"), str) and c["content"].strip():
                        return c["content"]

    body = resp.get("body")
    if isinstance(body, dict):
        if isinstance(body.get("output_text"), str) and body["output_text"].strip():
            return body["output_text"]
        out2 = body.get("output")
        if isinstance(out2, list):
            for item in out2:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for c in content:
                        if not isinstance(c, dict):
                            continue
                        if isinstance(c.get("text"), str) and c["text"].strip():
                            return c["text"]
    return None

def download_file_text(client, file_id):
    return client.files.content(file_id).read().decode("utf-8")

def load_state(state_path):
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {"submitted": {}, "done": {}, "failed": {}}

def save_state(state_path, state):
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

def consume_output_into_cache(output_jsonl_text, cache_path):
    wrote   = 0
    skipped = 0

    existing_keys = set()
    if cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    k = obj.get("key")
                    if k:
                        existing_keys.add(k)
                except Exception:
                    continue

    with cache_path.open("a", encoding="utf-8") as out:
        for line in output_jsonl_text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                skipped += 1
                continue

            cache_key = obj.get("custom_id") or obj.get("id")
            out_text  = extract_output_text(obj)
            if not cache_key or not out_text:
                skipped += 1
                continue

            if cache_key in existing_keys:
                skipped += 1
                continue

            try:
                data  = json.loads(out_text)
                qobjs = data.get("queries", [])
            except Exception:
                skipped += 1
                continue

            if not qobjs:
                skipped += 1
                continue

            out.write(json.dumps({"key": cache_key, "value": qobjs}, ensure_ascii=False) + "\n")
            existing_keys.add(cache_key)
            wrote += 1

    return wrote, skipped

def wait_for_batch(client, batch_id, poll_s):
    while True:
        b  = client.batches.retrieve(batch_id)
        rc = getattr(b, "request_counts", None)
        print(f"[poll] {batch_id} status={b.status} counts={rc}")
        if b.status in ("completed", "failed", "canceled", "expired"):
            return b
        time.sleep(poll_s)

def submit_one_batch(client, shard_path, completion_window):
    with shard_path.open("rb") as fh:
        file_obj = client.files.create(file=fh, purpose="batch")

    batch = client.batches.create(
        input_file_id     = file_obj.id,
        endpoint          = "/v1/responses",
        completion_window = completion_window
    )
    return {"batch_id": batch.id, "input_file_id": file_obj.id, "status": batch.status}

def list_shards_in_range(shard_dir, prefix, start, end):
    shards = sorted(shard_dir.glob(f"{prefix}_shard_*.jsonl"), key=shard_index)
    shards = [p for p in shards if start <= shard_index(p) <= end]
    return shards

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard_dir", required=True)
    ap.add_argument("--shard_prefix", default="openai_batch_input")
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--state_json", default="runner_state.json")
    ap.add_argument("--cache_path", default="llm_query_cache.jsonl")
    ap.add_argument("--completion_window", default="24h")
    ap.add_argument("--poll_s", type=int, default=60)
    ap.add_argument("--cooldown_s", type=int, default=15)
    ap.add_argument("--max_in_flight", type=int, default=1)
    ap.add_argument("--download_dir", default=None)
    args = ap.parse_args()

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENAI_API_KEY")

    client = OpenAI(api_key=key)

    shard_dir  = Path(args.shard_dir)
    state_path = Path(args.state_json)
    cache_path = Path(args.cache_path)

    dl_dir = Path(args.download_dir) if args.download_dir else (shard_dir / "downloads")
    dl_dir.mkdir(parents=True, exist_ok=True)

    state  = load_state(state_path)
    shards = list_shards_in_range(shard_dir, args.shard_prefix, args.start, args.end)

    print(f"Will process shards {args.start}..{args.end} ({len(shards)} file(s))")
    print(f"State: {state_path}")
    print(f"Downloads: {dl_dir}")
    print(f"Cache: {cache_path}")
    print(f"poll_s={args.poll_s} cooldown_s={args.cooldown_s} max_in_flight={args.max_in_flight}")

    for shard_path in shards:
        sidx = shard_index(shard_path)
        name = shard_path.name

        if name in state["done"]:
            print(f"[skip] shard {sidx:03d} already done")
            continue

        in_flight = 0
        for sname, meta in state["submitted"].items():
            if sname in state["done"] or sname in state["failed"]:
                continue

            fake_path = Path(sname)
            idx = shard_index(fake_path)
            if args.start <= idx <= args.end:
                in_flight += 1

        if name not in state["submitted"] and in_flight >= args.max_in_flight:
            print(f"[gate] in_flight={in_flight} >= max_in_flight={args.max_in_flight}")
            break

        if name in state["submitted"]:
            batch_id = state["submitted"][name]["batch_id"]
            print(f"[resume] shard {sidx:03d} already submitted batch_id={batch_id}")
        else:
            print(f"[submit] shard {sidx:03d} file={name} bytes={shard_path.stat().st_size}")
            meta = submit_one_batch(client, shard_path, args.completion_window)
            state["submitted"][name] = meta
            save_state(state_path, state)

            batch_id = meta["batch_id"]
            print(f"[submit] shard {sidx:03d} batch_id={batch_id}")
            time.sleep(args.cooldown_s)

        b = wait_for_batch(client, batch_id, args.poll_s)

        out_id = getattr(b, "output_file_id", None)
        err_id = getattr(b, "error_file_id", None)

        if b.status != "completed":
            if err_id:
                err_text = download_file_text(client, err_id)
                (dl_dir / f"{name}.errors.jsonl").write_text(err_text, encoding="utf-8")

            state["failed"][name] = {"batch_id": batch_id, "status": b.status, "error_file_id": err_id}
            save_state(state_path, state)
            print(f"[failed] shard {sidx:03d} status={b.status} error_file_id={err_id}")
            continue

        wrote = skipped = 0
        if out_id:
            out_text = download_file_text(client, out_id)
            (dl_dir / f"{name}.output.jsonl").write_text(out_text, encoding="utf-8")
            wrote, skipped = consume_output_into_cache(out_text, cache_path)

        if err_id:
            err_text = download_file_text(client, err_id)
            (dl_dir / f"{name}.errors.jsonl").write_text(err_text, encoding="utf-8")

        state["done"][name] = {
            "batch_id"      : batch_id,
            "status"        : b.status,
            "output_file_id": out_id,
            "error_file_id" : err_id,
            "cache_wrote"   : wrote,
            "cache_skipped" : skipped,
        }
        save_state(state_path, state)

        print(f"[done] shard {sidx:03d} cache_wrote={wrote} cache_skipped={skipped}")

    print("Runner finished this pass.")


if __name__ == "__main__":
    main()