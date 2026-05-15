import requests
from config import API_BASE_URL


def api_post(endpoint, data=None):
    try:
        response = requests.post(f"{API_BASE_URL}{endpoint}", json=data, timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def api_get(endpoint):
    try:
        response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def api_delete(endpoint):
    try:
        response = requests.delete(f"{API_BASE_URL}{endpoint}", timeout=5)
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def check_api_connection():
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=3)
        return response.status_code == 200
    except Exception:
        return False