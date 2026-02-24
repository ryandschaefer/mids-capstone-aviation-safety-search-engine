# mids-capstone-aviation-safety-search-engine



Usage:


python batch_runner.py \
  --shard_dir batch_all \
  --start 1 \
  --end 56 \
  --state_json batch_all/runner_state.json \
  --cache_path llm_query_cache.jsonl \
  --poll_s 60 \
  --max_in_flight 1


python finalize_from_cache.py --manifest batch_all/seed_manifest.json --out_dir .