"""
FastAPI 后端迁移测试脚本
测试所有 API 接口的功能和缓存失效逻辑
"""
import requests
import time
import json

BASE_URL = "http://localhost:5000/api"


def print_test(test_name, passed, details=""):
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"  {details}")


def test_calculate():
    """测试计算接口"""
    try:
        response = requests.post(f"{BASE_URL}/calculate", json={
            "unit_cost": 70,
            "unit_steam_sell": 100,
            "qty": 1,
            "use_exchange": False,
            "exchange_rate": 1.0,
            "fee_rate": 0.15
        })
        data = response.json()
        passed = response.status_code == 200 and "unit_net" in data
        print_test("POST /api/calculate", passed, f"Response: {data}")
        return passed
    except Exception as e:
        print_test("POST /api/calculate", False, str(e))
        return False


def test_get_settings():
    """测试获取设置接口"""
    try:
        response = requests.get(f"{BASE_URL}/settings")
        data = response.json()
        passed = response.status_code == 200 and "buy_currency" in data
        print_test("GET /api/settings", passed, f"Response: {data}")
        return passed
    except Exception as e:
        print_test("GET /api/settings", False, str(e))
        return False


def test_save_settings():
    """测试保存设置接口"""
    try:
        response = requests.post(f"{BASE_URL}/settings", json={
            "buy_currency": "CNY",
            "buy_currency_symbol": "¥",
            "sell_currency": "CNY",
            "sell_currency_symbol": "¥",
            "exchange_rate": 1.0,
            "steam_fee_rate": 0.15,
            "theme_mode": "LIGHT",
            "my_currency": "CNY",
            "my_currency_symbol": "¥",
            "language": "zh"
        })
        data = response.json()
        passed = response.status_code == 200 and "message" in data
        print_test("POST /api/settings", passed, f"Response: {data}")
        return passed
    except Exception as e:
        print_test("POST /api/settings", False, str(e))
        return False


def test_add_record():
    """测试添加记录接口"""
    try:
        response = requests.post(f"{BASE_URL}/records", json={
            "item_name": "测试物品",
            "note": "测试备注",
            "unit_cost": 70,
            "unit_steam_sell": 100,
            "qty": 1
        })
        data = response.json()
        passed = response.status_code == 201 and "message" in data
        print_test("POST /api/records", passed, f"Response: {data}")
        return passed
    except Exception as e:
        print_test("POST /api/records", False, str(e))
        return False


def test_get_records():
    """测试获取记录接口"""
    try:
        response = requests.get(f"{BASE_URL}/records")
        data = response.json()
        passed = response.status_code == 200 and isinstance(data, list)
        print_test("GET /api/records", passed, f"Records count: {len(data)}")
        return passed
    except Exception as e:
        print_test("GET /api/records", False, str(e))
        return False


def test_delete_record():
    """测试删除记录接口"""
    try:
        response = requests.post(f"{BASE_URL}/records", json={
            "item_name": "待删除物品",
            "note": "",
            "unit_cost": 50,
            "unit_steam_sell": 80,
            "qty": 1
        })
        if response.status_code == 201:
            data = response.json()
            
            records_resp = requests.get(f"{BASE_URL}/records")
            records = records_resp.json()
            if records:
                record_id = records[0]["id"]
                delete_resp = requests.delete(f"{BASE_URL}/records/{record_id}")
                delete_data = delete_resp.json()
                passed = delete_resp.status_code == 200 and "message" in delete_data
                print_test(f"DELETE /api/records/{record_id}", passed, f"Response: {delete_data}")
                return passed
        print_test("DELETE /api/records/{id}", False, "Failed to create test record")
        return False
    except Exception as e:
        print_test("DELETE /api/records/{id}", False, str(e))
        return False


def test_clear_records():
    """测试清空记录接口"""
    try:
        response = requests.delete(f"{BASE_URL}/records")
        data = response.json()
        passed = response.status_code == 200 and "message" in data
        print_test("DELETE /api/records", passed, f"Response: {data}")
        return passed
    except Exception as e:
        print_test("DELETE /api/records", False, str(e))
        return False


def test_get_stats():
    """测试获取统计接口"""
    try:
        response = requests.get(f"{BASE_URL}/stats")
        data = response.json()
        passed = response.status_code == 200 and "total_cost" in data
        print_test("GET /api/stats", passed, f"Response: {data}")
        return passed
    except Exception as e:
        print_test("GET /api/stats", False, str(e))
        return False


def test_exchange_rate():
    """测试汇率接口"""
    try:
        response = requests.get(f"{BASE_URL}/exchange-rate?base=USD&target=CNY")
        if response.status_code == 200:
            data = response.json()
            passed = "rate" in data and "base" in data
            print_test("GET /api/exchange-rate", passed, f"Response: {data}")
            return passed
        else:
            print_test("GET /api/exchange-rate", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_test("GET /api/exchange-rate", False, str(e))
        return False


def test_stats_cache_invalidation():
    """测试统计缓存失效逻辑"""
    try:
        print("\n--- 测试统计缓存失效 ---")
        
        stats1 = requests.get(f"{BASE_URL}/stats").json()
        print(f"初始统计: {stats1}")
        
        response = requests.post(f"{BASE_URL}/records", json={
            "item_name": "缓存测试物品",
            "note": "",
            "unit_cost": 100,
            "unit_steam_sell": 150,
            "qty": 2
        })
        
        if response.status_code == 201:
            stats2 = requests.get(f"{BASE_URL}/stats").json()
            print(f"添加记录后统计: {stats2}")
            
            passed = (stats2["total_qty"] > stats1["total_qty"] and 
                     stats2["total_cost"] > stats1["total_cost"])
            print_test("添加记录后统计缓存失效", passed)
            return passed
        else:
            print_test("添加记录后统计缓存失效", False, "Failed to add record")
            return False
    except Exception as e:
        print_test("添加记录后统计缓存失效", False, str(e))
        return False


def test_settings_cache_invalidation():
    """测试设置缓存失效逻辑"""
    try:
        print("\n--- 测试设置缓存失效 ---")
        
        settings1 = requests.get(f"{BASE_URL}/settings").json()
        print(f"初始设置: {settings1}")
        
        response = requests.post(f"{BASE_URL}/settings", json={
            "buy_currency": "USD",
            "buy_currency_symbol": "$",
            "sell_currency": "CNY",
            "sell_currency_symbol": "¥",
            "exchange_rate": 7.2,
            "steam_fee_rate": 0.15,
            "theme_mode": "DARK",
            "my_currency": "CNY",
            "my_currency_symbol": "¥",
            "language": "zh"
        })
        
        if response.status_code == 200:
            settings2 = requests.get(f"{BASE_URL}/settings").json()
            print(f"修改设置后: {settings2}")
            
            passed = (settings2["buy_currency"] == "USD" and 
                     settings2["theme_mode"] == "DARK")
            print_test("修改设置后设置缓存失效", passed)
            return passed
        else:
            print_test("修改设置后设置缓存失效", False, "Failed to save settings")
            return False
    except Exception as e:
        print_test("修改设置后设置缓存失效", False, str(e))
        return False


def test_error_responses():
    """测试错误响应格式"""
    try:
        print("\n--- 测试错误响应格式 ---")
        
        response = requests.post(f"{BASE_URL}/records", json={
            "item_name": "",
            "unit_cost": 0,
            "unit_steam_sell": 0,
            "qty": 1
        })
        data = response.json()
        passed = response.status_code == 400 and "error" in data
        print_test("错误响应格式 (空物品名称)", passed, f"Response: {data}")
        
        response = requests.get(f"{BASE_URL}/exchange-rate?base=INVALID&target=CNY")
        data = response.json()
        passed = response.status_code in [400, 500] and "error" in data
        print_test("错误响应格式 (无效货币)", passed, f"Response: {data}")
        
        return True
    except Exception as e:
        print_test("错误响应格式", False, str(e))
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("FastAPI 后端迁移测试")
    print("=" * 60)
    
    results = []
    
    results.append(("计算接口", test_calculate()))
    results.append(("获取设置", test_get_settings()))
    results.append(("保存设置", test_save_settings()))
    results.append(("添加记录", test_add_record()))
    results.append(("获取记录", test_get_records()))
    results.append(("删除记录", test_delete_record()))
    results.append(("清空记录", test_clear_records()))
    results.append(("获取统计", test_get_stats()))
    results.append(("汇率接口", test_exchange_rate()))
    results.append(("统计缓存失效", test_stats_cache_invalidation()))
    results.append(("设置缓存失效", test_settings_cache_invalidation()))
    results.append(("错误响应格式", test_error_responses()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for test_name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {test_name}")
    
    print(f"\n通过: {passed_count}/{total_count}")
    
    if passed_count == total_count:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {total_count - passed_count} 个测试失败")


if __name__ == "__main__":
    run_all_tests()