import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE_URL = "http://localhost:5000/api"

# 请求缓存和去重机制
_request_cache = {}
_cache_lock = threading.Lock()
_ongoing_requests = {}  # 正在进行的请求跟踪


def api_get(endpoint: str, cache_ttl=1.0):
    """
    带缓存和防抖的 GET 请求
    cache_ttl: 缓存有效期（秒），默认 1 秒防止快速重复请求
    """
    current_time = time.time()
    cache_key = f"GET:{endpoint}"

    # 检查缓存
    with _cache_lock:
        if cache_key in _request_cache:
            data, status, cached_time = _request_cache[cache_key]
            if current_time - cached_time < cache_ttl:
                return data, status

        # 检查是否有相同请求正在进行
        if cache_key in _ongoing_requests:
            # 等待已有请求完成
            start_wait = current_time
            while cache_key in _ongoing_requests and time.time() - start_wait < 5:
                time.sleep(0.05)
            # 等待完成后检查是否有缓存结果
            if cache_key in _request_cache:
                data, status, cached_time = _request_cache[cache_key]
                if current_time - cached_time < cache_ttl:
                    return data, status

        # 标记请求开始
        _ongoing_requests[cache_key] = True

    try:
        resp = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
        result = resp.json() if resp.status_code in (200, 201) else {}, resp.status_code

        # 缓存成功结果
        if resp.status_code in (200, 201):
            with _cache_lock:
                _request_cache[cache_key] = (result[0], result[1], time.time())

        return result
    except Exception:
        return {}, 0
    finally:
        # 清除进行中标记
        with _cache_lock:
            _ongoing_requests.pop(cache_key, None)


def invalidate_cache(endpoint=None):
    """清除请求缓存，如果不指定 endpoint 则清除所有缓存"""
    with _cache_lock:
        if endpoint is None:
            _request_cache.clear()
        else:
            cache_key = f"GET:{endpoint}"
            _request_cache.pop(cache_key, None)


def api_post(endpoint: str, payload: dict):
    try:
        resp = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, timeout=10)
        return resp.json() if resp.status_code in (200, 201) else {}, resp.status_code
    except Exception:
        return {}, 0


def api_delete(endpoint: str):
    try:
        resp = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=5)
        return resp.json() if resp.status_code == 200 else {}, resp.status_code
    except Exception:
        return {}, 0


def check_api_connection():
    try:
        resp = requests.get(f"{API_BASE_URL}/settings", timeout=2)
        return resp.status_code == 200
    except Exception:
        return False


def api_get_parallel(endpoints: list):
    """并发执行多个 GET 请求，返回 [(data, status), ...] 列表，顺序与 endpoints 一致。"""
    results = [({}, 0) for _ in endpoints]

    def fetch(idx_endpoint):
        idx, endpoint = idx_endpoint
        results[idx] = api_get(endpoint)

    with ThreadPoolExecutor(max_workers=len(endpoints)) as executor:
        executor.map(fetch, enumerate(endpoints))

    return results
