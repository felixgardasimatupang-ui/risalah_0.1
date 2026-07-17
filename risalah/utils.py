import functools
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor


def retry(max_attempts=3, delay=2, backoff=2, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts - 1:
                        wait = delay * (backoff**attempt)
                        print(f"  Retry {attempt + 1}/{max_attempts} after {wait}s: {e}")
                        time.sleep(wait)
                    else:
                        print(f"  Gagal setelah {max_attempts} percobaan: {e}")
            raise last_exc

        return wrapper

    return decorator


def run_parallel(func1, func2, timeout=7200):
    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(func1)
        f2 = ex.submit(func2)
        return f1.result(timeout=timeout), f2.result(timeout=timeout)


def cache_check(cache_dir, key_name, data_loader, overwrite=False):
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"cache_{key_name}.json")
    if os.path.exists(cache_path) and not overwrite:
        with open(cache_path) as f:
            print(f"  Cache HIT: {key_name}")
            return json.load(f)
    if overwrite:
        print(f"  Cache OVERWRITE: {key_name}")
    else:
        print(f"  Cache MISS: {key_name}")
    data = data_loader()
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data


def make_cache_key(*parts):
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()[:16]
