# Steam 倒余额工具箱
 ![visitors](https://visitor-badge.laobi.icu/badge?page_id=linyaocrush/steam-flip-calculator)
 ![GitHub License](https://img.shields.io/github/license/linyaocrush/steam-flip-calculator)
 ![GitHub last commit](https://img.shields.io/github/last-commit/linyaocrush/steam-flip-calculator)
 ![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)

一个基于 Flet 的 Steam 市场倒余额计算工具，帮助您计算 Steam 市场交易的利润、折扣和汇率转换。采用 Google MD3 风格设计，带有毛玻璃效果。

## 功能特性

- 🧮 **计算器**：计算 Steam 市场交易的利润和折扣率
- 📊 **历史记录**：保存和管理交易记录，支持倒余额比例显示
- 📈 **统计汇总**：查看整体交易统计信息
- ⚙️ **多语言支持**：支持中文、英文、日文界面
- 🌍 **多货币支持**：支持 10 种主流货币
- 💱 **自动汇率**：自动获取实时汇率
- 🌙 **深色主题**：采用深色模式设计
- ✨ **毛玻璃效果**：现代化的玻璃拟态 UI 设计
- 🔄 **状态管理**：基于 AppState 的统一状态管理
- 📦 **数据库迁移**：版本化的数据库结构管理

## 支持的货币

- CNY - 人民币 (¥)
- USD - 美元 ($)
- JPY - 日元 (¥)
- EUR - 欧元 (€)
- GBP - 英镑 (£)
- KRW - 韩元 (₩)
- HKD - 港币 (HK$)
- AUD - 澳元 (A$)
- CAD - 加元 (C$)
- SGD - 新加坡元 (S$)

## 安装

### 前置要求

- Python 3.8 或更高版本

### 安装步骤

1. 克隆或下载项目到本地

2. 创建虚拟环境：
   ```bash
   python -m venv venv
   ```

3. 激活虚拟环境：
   ```bash
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

4. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

5. 运行应用：
   ```bash
   python main.py
   ```

## 使用说明

### 计算器

1. 输入物品名称和备注（可选）
2. 输入第三方平台购买成本（单价）
3. 输入 Steam 市场售出价格（单价）
4. 输入购买数量
5. 查看计算结果：
   - Steam 实际到账金额（扣除手续费）
   - 总花费和总到手余额
   - 倒余额比例和折扣率
6. 点击"记录到历史"保存交易记录

### 历史记录

- 查看所有保存的交易记录
- 支持删除单条记录
- 支持清空全部记录
- 显示每条记录的详细信息，包括倒余额比例

### 统计

- 查看所有历史记录的汇总统计
- 总数量、总花费、总售出金额
- 总到手余额和整体折扣率

### 设置

- **买入货币**：第三方平台购买物品使用的货币
- **卖出货币**：Steam 市场所在区域的货币
- **汇率**：自动获取或手动设置汇率
- **手续费率**：Steam 市场手续费（默认 15%）
- **我的货币**：价格显示时自动转换的货币
- **语言**：选择界面显示语言

## 项目结构

```
steam-flip-calculator/
├── main.py                          # 主程序入口
├── requirements.txt                 # 依赖列表
├── data/
│   └── steam_flip.db                # SQLite 数据库（运行后自动生成）
├── src/                             # 源代码目录
│   ├── config/                      # 配置模块
│   │   └── __init__.py              # 默认设置和常量
│   ├── models/                      # 数据模型
│   │   └── __init__.py              # Pydantic 模型定义
│   ├── services/                    # 业务服务
│   │   ├── calculator.py            # 计算逻辑
│   │   ├── database.py              # 数据库操作
│   │   ├── exchange_rate.py         # 汇率获取
│   │   └── migrations.py            # 数据库迁移
│   ├── state/                       # 状态管理
│   │   └── app_state.py             # AppState 单例
│   ├── ui/                          # UI 组件
│   │   └── glassmorphism.py         # 毛玻璃效果组件
│   ├── utils/                       # 工具函数
│   │   ├── __init__.py              # 通用工具函数
│   │   └── i18n.py                  # 国际化
│   └── views/                       # 视图组件
│       ├── __init__.py              # 视图导出
│       ├── calculator_view.py       # 计算器视图
│       ├── history_view.py          # 历史记录视图
│       ├── settings_view.py         # 设置视图
│       └── stats_view.py            # 统计视图
```

## 技术栈

- **Flet**：跨平台 UI 框架
- **SQLite**：本地数据存储
- **Pydantic**：数据验证和模型
- **Requests**：HTTP 请求（获取汇率）

## 数据库结构

### history 表（历史记录）

优化后的结构，使用 JSON 快照减少冗余：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| ts | TEXT | 时间戳 |
| item_name | TEXT | 物品名称 |
| note | TEXT | 备注 |
| unit_cost | REAL | 单位成本 |
| unit_steam_sell | REAL | 单位Steam售价 |
| qty | INTEGER | 数量 |
| unit_net | REAL | 单位净收入 |
| total_cost | REAL | 总成本 |
| total_steam_sell | REAL | 总Steam售价 |
| total_net | REAL | 总净收入 |
| discount | REAL | 折扣率 |
| ratio | REAL | 翻转比率 |
| settings_snapshot | TEXT | 设置快照（JSON格式） |
| calculation_snapshot | TEXT | 计算结果快照（JSON格式） |
| created_at | TEXT | 创建时间 |


## 状态管理

项目使用 `AppState` 单例模式进行统一的状态管理：

```python
from src.state.app_state import app_state

# 获取设置
settings = app_state.get_settings()

# 更新设置（会自动触发事件广播）
app_state.update_settings({"buy_currency": "CNY"})

# 订阅设置变化
def on_settings_changed(new_settings):
    # 刷新UI
    pass

unsubscribe = app_state.subscribe(on_settings_changed)
```

## 汇率数据

汇率数据来自 [Frankfurter API](https://frankfurter.dev/)，一个免费的汇率 API。

## 许可证

本项目仅供学习和个人使用。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v2.0.0 (2026-05-18)

- 🔄 重构项目结构，按功能模块化
- 📦 引入 AppState 状态管理系统
- 🗄️ 优化数据库结构，使用 JSON 快照减少冗余
- 🚀 添加数据库迁移机制
- 🎨 改进货币符号显示逻辑
- 🐛 修复折扣计算错误
- 🐛 修复设置变更后货币符号不更新的问题

### v1.0.0

- 🎉 初始版本发布
- ✨ 基础计算功能
- 📊 历史记录和统计
- 🌍 多语言和多货币支持