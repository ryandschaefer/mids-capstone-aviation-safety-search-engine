import random


class MetadataNeighborMiner:

    def __init__(self, cfg, loader):
        self.cfg = cfg
        self.loader = loader
        self.corpus_df = None
        self.rng = random.Random(cfg.seed)

        self.anom_col  = "Events_Anomaly"
        self.phase_col = "Aircraft 1.9_Flight Phase"

        self.other_bucket_cols = [
            "Assessments_Contributing Factors / Situations",
            "Person 1.7_Human Factors",
            "Events.5_Result",
        ]

        self.boost_cols = [
            "Place_Locale Reference",
            "Place.1_State Reference",
            "Aircraft 1.2_Make Model Name",
        ]

        self.W_ANOM = 10
        self.W_PHASE_MATCH = 6
        self.W_BUCKET_OVERLAP = 2
        self.W_BOOST = 1

        self.MAX_PER_AIRPORT = 5

        self._meta = []
        self._anom_sets = []
        self._id = []
        self._phase = []
        self._airport = []
        self._boost_vals = {}
        self._anom_to_idx = {}

    @staticmethod
    def _to_set(v):
        if v is None:
            return set()
        if isinstance(v, list):
            return {str(x).strip() for x in v if str(x).strip()}
        s = str(v).strip()
        if not s or s.lower() == "nan":
            return set()
        if ";" in s:
            return {p.strip() for p in s.split(";") if p.strip()}
        return {s}

    @staticmethod
    def _clean(v):
        s = str(v).strip()
        if not s or s.lower() == "nan":
            return ""
        return s

    def fit(self, corpus_df):
        self.corpus_df = corpus_df.reset_index(drop=True)
        df = self.corpus_df
        id_col = self.cfg.id_col

        self._meta = []
        self._anom_sets = []
        self._id = df[id_col].astype(str).tolist()
        self._phase = [self._clean(x) for x in df.get(self.phase_col, [""] * len(df))]
        self._airport = [self._clean(x) for x in df.get("Place_Locale Reference", [""] * len(df))]

        self._boost_vals = {c: [self._clean(x) for x in df.get(c, [""] * len(df))] for c in self.boost_cols}

        self._anom_to_idx = {}

        for i in range(len(df)):
            m = self.loader.build_metadata(df.iloc[i], bucket=True)
            self._meta.append(m)

            aset = self._to_set(m.get(self.anom_col))
            self._anom_sets.append(aset)

            for a in aset:
                self._anom_to_idx.setdefault(a, []).append(i)

        return self

    def neighbors_with_rels(self, seed_row, k):
        seed_id = str(seed_row[self.cfg.id_col])
        seed_meta = self.loader.build_metadata(seed_row, bucket=True)
        seed_anom = self._to_set(seed_meta.get(self.anom_col))
        if not seed_anom:
            return []

        seed_phase = self._clean(seed_row.get(self.phase_col, ""))
        seed_boost = {c: self._clean(seed_row.get(c, "")) for c in self.boost_cols}

        cand_idx = set()
        for a in seed_anom:
            cand_idx.update(self._anom_to_idx.get(a, []))

        scored = []
        for i in cand_idx:
            did = self._id[i]
            if did == seed_id:
                continue

            anom_overlap = len(seed_anom & self._anom_sets[i])
            if anom_overlap == 0:
                continue

            score = self.W_ANOM * anom_overlap

            same_phase = (seed_phase != "" and self._phase[i] == seed_phase)
            if same_phase:
                score += self.W_PHASE_MATCH

            m = self._meta[i]
            for bcol in self.other_bucket_cols:
                score += self.W_BUCKET_OVERLAP * len(self._to_set(seed_meta.get(bcol)) & self._to_set(m.get(bcol)))

            for c in self.boost_cols:
                sv = seed_boost.get(c, "")
                if sv and self._boost_vals[c][i] == sv:
                    score += self.W_BOOST

            rel = 2 if same_phase else 1
            scored.append((i, rel, score))

        scored.sort(key=lambda x: (x[1], x[2]), reverse=True)

        out = []
        per_airport = {}
        for i, rel, score in scored:
            airport = self._airport[i]
            if airport:
                if per_airport.get(airport, 0) >= self.MAX_PER_AIRPORT:
                    continue
                per_airport[airport] = per_airport.get(airport, 0) + 1

            out.append((self._id[i], rel))
            if len(out) >= k:
                break

        return out

    def neighbors(self, seed_row, k):
        return [did for did, _ in self.neighbors_with_rels(seed_row, k)]