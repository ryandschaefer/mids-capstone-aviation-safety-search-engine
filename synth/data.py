import json
import numpy as np
from datasets import concatenate_datasets, load_dataset


class ASRSLoader:

    KEEP_COLS = [
        "acn_num_ACN",
        "Time_Date",
        "Place.1_State Reference",
        "Place_Locale Reference",
        "Aircraft 1.2_Make Model Name",
        "Aircraft 1.9_Flight Phase",
        "Aircraft 1.5_Operating Under FAR Part",
        "Aircraft 1.6_Flight Plan",
        "Aircraft 1.7_Mission",
        "Aircraft 1.1_Aircraft Operator",
        "Aircraft 1.11_Airspace",
        "Aircraft 1_ATC / Advisory",
        "Environment_Flight Conditions",
        "Environment.3_Light",
        "Events.4_When Detected",
        "Events.3_Detector",
        "Component_Aircraft Component",
        "Component.3_Problem",
        "Assessments.1_Primary Problem",
    ]

    BUCKET_COLS = [
        "Events_Anomaly",
        "Assessments_Contributing Factors / Situations",
        "Person 1.7_Human Factors",
        "Events.5_Result",
    ]

    def __init__(self, cfg):
        self.cfg = cfg

        self.df      = None
        self.columns = None

        self.keep_cols_present   = []
        self.bucket_cols_present = []

        self.train_df = None
        self.val_df   = None
        self.test_df  = None

    def load(self):
        ds     = load_dataset(self.cfg.dataset_name)
        ds_all = concatenate_datasets([ds[k] for k in ds.keys()])
        df     = ds_all.to_pandas()

        self.columns = list(df.columns)

        self.keep_cols_present   = [c for c in self.KEEP_COLS if c in df.columns]
        self.bucket_cols_present = [c for c in self.BUCKET_COLS if c in df.columns]

        df[self.cfg.id_col]        = df[self.cfg.id_col].astype(str)
        df[self.cfg.narrative_col] = df[self.cfg.narrative_col].fillna("").astype(str)
        df[self.cfg.synopsis_col]  = df[self.cfg.synopsis_col].fillna("").astype(str)

        df = df[(df[self.cfg.narrative_col].str.len() > 0) & (df[self.cfg.synopsis_col].str.len() > 0)].reset_index(drop=True)

        self.df = df
        self._build_splits()
        return self

    def _build_splits(self):
        cfg = self.cfg
        rng = np.random.default_rng(cfg.seed)

        idx = np.arange(len(self.df))
        rng.shuffle(idx)

        n       = len(idx)
        n_train = int(0.70 * n)
        n_val   = int(0.15 * n)

        train_idx = idx[:n_train]
        val_idx   = idx[n_train : n_train + n_val]
        test_idx  = idx[n_train + n_val :]

        self.train_df = self.df.iloc[train_idx].reset_index(drop=True)
        self.val_df   = self.df.iloc[val_idx].reset_index(drop=True)
        self.test_df  = self.df.iloc[test_idx].reset_index(drop=True)

    @staticmethod
    def _clean_str(x):
        if x is None:
            return ""
        if isinstance(x, float) and np.isnan(x):
            return ""
        s = str(x).strip()
        if not s or s.lower() == "nan":
            return ""
        return s

    @staticmethod
    def _split_semicolon_list(s):
        parts = [p.strip() for p in s.split(";")]
        seen  = set()
        out   = []
        for p in parts:
            if p and p.lower() != "nan" and p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def build_metadata(self, row, bucket=True):
        cfg  = self.cfg
        meta = {}

        for c in self.keep_cols_present:
            v = self._clean_str(row.get(c, ""))
            if v:
                meta[c] = v

        for c in self.bucket_cols_present:
            v = self._clean_str(row.get(c, ""))
            if not v:
                continue
            meta[c] = self._split_semicolon_list(v) if bucket else v

        if cfg.time_col in meta:
            t = meta[cfg.time_col]
            if len(t) >= 4:
                meta["Year"] = t[:4]
            if len(t) >= 6:
                meta["YearMonth"] = t[:6]

        return meta

    def build_record(self, row):
        cfg = self.cfg

        rec = {
            "id"       : self._clean_str(row.get(cfg.id_col, "")),
            "time"     : self._clean_str(row.get(cfg.time_col, "")) if cfg.time_col in row else "",
            "synopsis" : self._clean_str(row.get(cfg.synopsis_col, "")),
            "narrative": self._clean_str(row.get(cfg.narrative_col, "")),
            "metadata" : self.build_metadata(row, bucket=True),
        }

        record_json = json.dumps(rec, ensure_ascii=False)
        if len(record_json) <= cfg.max_record_chars:
            return {"record_json": record_json, "record_obj": rec}

        rec_small = {
            "id"       : rec["id"],
            "time"     : rec.get("time", ""),
            "synopsis" : rec["synopsis"][:1500],
            "narrative": rec["narrative"][:4000],
            "metadata" : rec["metadata"],
        }

        return {
            "record_json": json.dumps(rec_small, ensure_ascii=False),
            "record_obj" : rec_small,
        }

    def build_corpus_df(self, df):
        cfg  = self.cfg
        cols = [cfg.id_col, cfg.narrative_col, cfg.synopsis_col]

        if cfg.time_col in df.columns:
            cols.append(cfg.time_col)

        out = df[cols].copy()
        out.rename(columns={
                cfg.id_col       : "doc_id",
                cfg.narrative_col: "narrative",
                cfg.synopsis_col : "synopsis",
                cfg.time_col     : "time",
            },
            inplace=True,
        )

        out["metadata_json"] = [
            json.dumps(self.build_metadata(r, bucket=True), ensure_ascii=False)
            for _, r in df.iterrows()
        ]

        return out