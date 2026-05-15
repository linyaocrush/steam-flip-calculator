import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE_URL = "http://localhost:5000/api"


def api_get(endpoint: str):
    try:
        resp = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
        return resp.json() if resp.status_code in (200, 201) else {}, resp.status_code
    except Exception:
        return {}, 0


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
