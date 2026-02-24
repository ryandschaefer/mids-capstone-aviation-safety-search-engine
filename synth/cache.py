import json
import os


class JSONLCache:

    def __init__(self, path):
        self.path = path
        self.mem  = self._load()

    def _load(self):
        out = {}
        if not os.path.exists(self.path):
            return out

        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    out[obj["key"]] = obj["value"]
                except Exception:
                    continue
        return out

    def get(self, key):
        return self.mem.get(key)

    def set(self, key, value):
        self.mem[key] = value
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")