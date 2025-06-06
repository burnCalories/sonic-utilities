import os
import json

from natsort import natsorted
from tabulate import tabulate
from swsscommon.swsscommon import SonicV2Connector
from utilities_common.cli import UserCache


class SRv6Stat(object):
    COUNTERS_CACHE_FILE = "srv6stat"
    SRV6_COUNTERS_MAP = "COUNTERS_SRV6_NAME_MAP"
    COUNTERS_TABLE = "COUNTERS"
    TABLE_HEADER = ["MySID", "Packets", "Bytes"]
    COUNTER_PACKETS = "SAI_COUNTER_STAT_PACKETS"
    COUNTER_BYTES = "SAI_COUNTER_STAT_BYTES"

    def __init__(self):
        self.db = SonicV2Connector()
        self.db.connect(self.db.COUNTERS_DB)
        self.user_cache = UserCache()
        self.user_cache_file = os.path.join(self.user_cache.get_directory(), self.COUNTERS_CACHE_FILE)
        self.cache_is_invalid = False

    def get_counters_map(self, sid=None):
        if self.db.exists(self.db.COUNTERS_DB, self.SRV6_COUNTERS_MAP):
            if sid:
                sid_info = self.db.get(self.db.COUNTERS_DB, self.SRV6_COUNTERS_MAP, sid)
                return {sid: sid_info} if sid_info else {}
            return self.db.get_all(self.db.COUNTERS_DB, self.SRV6_COUNTERS_MAP)
        return {}

    def fetch_counters(self, sid=None):
        data = {}
        counters_db_separator = self.db.get_db_separator(self.db.COUNTERS_DB)
        counters_map = self.get_counters_map(sid)
        for entry, counter_oid in counters_map.items():
            counter_key = f'{self.COUNTERS_TABLE}{counters_db_separator}{counter_oid}'
            counter_stats = self.db.get_all(self.db.COUNTERS_DB, counter_key)
            if counter_stats:
                data[entry] = counter_stats
        return data

    def fetch_saved_counters(self):
        if os.path.isfile(self.user_cache_file):
            try:
                with open(self.user_cache_file) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_counter_value(self, key, stats, saved_stats, stat_type):
        old_value = saved_stats.get(key, {}).get(stat_type, '0')
        db_value = stats[stat_type]
        diff = int(db_value) - int(old_value)
        if diff < 0:
            self.cache_is_invalid = True
            return db_value
        return diff

    def show(self, sid=None):
        counters = self.fetch_counters(sid)
        saved_counters = self.fetch_saved_counters()
        srv6stats = []
        for entry, stats in counters.items():
            packets = self.get_counter_value(entry, stats, saved_counters, self.COUNTER_PACKETS)
            bytes = self.get_counter_value(entry, stats, saved_counters, self.COUNTER_BYTES)
            srv6stats.append([entry, packets, bytes])
        print(tabulate(natsorted(srv6stats), self.TABLE_HEADER))

        if self.cache_is_invalid:
            self.remove_cache()

    def remove_cache(self):
        self.user_cache.remove_all()
        self.cache_is_invalid = False

    def clear(self):
        counters = self.fetch_counters()
        with open(self.user_cache_file, 'w') as f:
            json.dump(counters, f)
