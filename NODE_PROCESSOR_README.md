# 节点筛选和测速系统

## 📋 功能说明

本系统在原有订阅收集功能基础上，新增了节点筛选和测速功能。

### 工作流程

```
1. 订阅收集 (fetch.yaml)
   每6小时运行一次
   ↓
   抓取 Telegram 频道订阅链接
   ↓
   保存到 sub/ 目录

2. 节点处理 (process_nodes.yaml)
   每6小时运行一次（比订阅收集晚30分钟）
   ↓
   下载所有订阅内容
   ↓
   解析节点（支持 Clash/VMess/SS/Trojan/SSR）
   ↓
   第一次筛选：
   ❌ 过滤纯IP节点
   ❌ 过滤80端口节点
   ❌ 过滤443端口节点
   ✅ 只保留域名节点
   ↓
   TCP测速（64线程并发）
   ↓
   第二次筛选：
   ❌ 过滤超时节点
   ❌ 过滤延迟>3000ms节点
   ✅ 只保留可用节点
   ↓
   输出到主目录
```

## 📁 输出文件

- `available_nodes_clash.yaml` - Clash 格式可用节点
- `available_nodes_base64.txt` - Base64 格式可用节点（兼容 V2Ray/Shadowrocket）

## 🔧 本地测试

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行节点处理
python node_processor.py
```

## 📦 新增文件

- `node_filter.py` - 节点解析和筛选模块
- `node_speedtest.py` - TCP测速模块
- `node_processor.py` - 主处理程序
- `.github/workflows/process_nodes.yaml` - GitHub Actions 工作流

## ⚙️ 配置说明

### 筛选规则

在 `node_filter.py` 中修改：

```python
def filter_node(node):
    # 修改端口过滤规则
    if port in [80, 443]:  # 可以添加更多端口
        return False
```

### 测速参数

在 `node_speedtest.py` 中修改：

```python
def tcp_test(server, port, timeout=5):  # 修改超时时间
    ...

def test_node(node, results, bar):
    if latency > 0 and latency < 3000:  # 修改延迟阈值
        ...
```

### 并发数量

在 `node_speedtest.py` 中修改：

```python
thread_max_num = threading.Semaphore(64)  # 修改并发线程数
```

## 🚀 GitHub Actions

### 手动触发

1. 进入 GitHub 仓库
2. 点击 Actions 标签
3. 选择 "Process Nodes - Filter and Speed Test"
4. 点击 "Run workflow"

### 自动运行

- 订阅收集：每6小时的第5分钟运行
- 节点处理：每6小时的第30分钟运行

## 📊 性能指标

- 订阅链接数：~7000+
- 原始节点数：~10000-50000
- 第一次筛选后：~3000-15000
- 测速后可用节点：~500-3000
- 处理时间：约10-30分钟

## ⚠️ 注意事项

1. GitHub Actions 有运行时间限制（6小时），如果订阅链接过多可能超时
2. 测速使用 TCP 连接测试，不是实际代理测试
3. 节点可用性会随时间变化，建议定期更新
4. 输出文件会自动提交到仓库主目录
