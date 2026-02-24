import argparse
import json
import pandas as pd

from synth import BuildConfig, ASRSLoader, IRDatasetBuilder


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--cache_path", default="llm_query_cache.jsonl")
    ap.add_argument("--out_dir", default=".")
    args = ap.parse_args()

    cfg = BuildConfig(
        cache_path         = args.cache_path,
        openai_model       = "gpt-5-nano",
        seed               = 42,
        queries_per_doc    = 1,
        meta_pos_per_query = 20,
        seed_rel           = 2
    )

    man     = json.load(open(args.manifest, "r", encoding="utf-8"))
    loader  = ASRSLoader(cfg).load()
    builder = IRDatasetBuilder(cfg, loader=loader)

    train_df, val_df, test_df = loader.train_df, loader.val_df, loader.test_df
    all_df = pd.concat([train_df, val_df, test_df], ignore_index=True)

    train_ids = set(map(str, man["splits"]["train"]["seed_ids"]))
    val_ids   = set(map(str, man["splits"]["val"]["seed_ids"]))
    test_ids  = set(map(str, man["splits"]["test"]["seed_ids"]))

    train_prefix = man["splits"]["train"]["prefix"]
    val_prefix   = man["splits"]["val"]["prefix"]
    test_prefix  = man["splits"]["test"]["prefix"]

    train_seed = train_df[train_df[cfg.id_col].astype(str).isin(train_ids)].reset_index(drop=True)
    val_seed   = val_df[val_df[cfg.id_col].astype(str).isin(val_ids)].reset_index(drop=True)
    test_seed  = test_df[test_df[cfg.id_col].astype(str).isin(test_ids)].reset_index(drop=True)

    train_q, train_r, corpus_export = builder.finalize_from_cache(
        corpus_df        = all_df,
        seed_df          = train_seed,
        cache_key_prefix = train_prefix,
    )

    val_q, val_r, _ = builder.finalize_from_cache(
        corpus_df        = all_df,
        seed_df          = val_seed,
        cache_key_prefix = val_prefix,
    )

    test_q, test_r, _ = builder.finalize_from_cache(
        corpus_df        = all_df,
        seed_df          = test_seed,
        cache_key_prefix = test_prefix,
    )

    out = args.out_dir.rstrip("/")

    corpus_export.to_csv(f"{out}/corpus.csv", index=False)
    train_q.to_csv(f"{out}/queries_train.csv", index=False)
    train_r.to_csv(f"{out}/qrels_train.csv", index=False)
    val_q.to_csv(f"{out}/queries_val.csv", index=False)
    val_r.to_csv(f"{out}/qrels_val.csv", index=False)
    test_q.to_csv(f"{out}/queries_test.csv", index=False)
    test_r.to_csv(f"{out}/qrels_test.csv", index=False)

    print("Finalized CSVs:")
    print("train:", train_q.shape, train_r.shape)
    print("val:  ", val_q.shape, val_r.shape)
    print("test: ", test_q.shape, test_r.shape)
    print("corpus:", corpus_export.shape)


if __name__ == "__main__":
    main()

# scp -r /Users/ronald/Desktop/search-engine/llm_query_cache.jsonl rnap@login.rc.ucmerced.edu:/home/rnap/capstone/
# scp -r /Users/ronald/Desktop/search-engine/batch_all/seed_manifest.json rnap@login.rc.ucmerced.edu:/home/rnap/capstone/