# 🚀 使用指南

## 快速开始

### 1. Fork 本仓库到你的 GitHub 账号

### 2. 启用 GitHub Actions

1. 进入你的仓库
2. 点击 "Actions" 标签
3. 点击 "I understand my workflows, go ahead and enable them"

### 3. 查看运行状态

#### 订阅收集 (Fetch Subscriptions Source)
- 自动运行：每6小时的第5分钟
- 手动运行：Actions → Fetch Subscriptions Source → Run workflow
- 输出：`sub/` 目录下的订阅链接文件

#### 节点处理 (Process Nodes - Filter and Speed Test)
- 自动运行：每6小时的第30分钟（在订阅收集后）
- 手动运行：Actions → Process Nodes → Run workflow
- 输出：
  - `available_nodes_clash.yaml` - Clash 格式
  - `available_nodes_base64.txt` - Base64 格式

### 4. 获取可用节点

#### 方式1：直接下载文件
```
https://raw.githubusercontent.com/你的用户名/collectSub-main/main/available_nodes_clash.yaml
https://raw.githubusercontent.com/你的用户名/collectSub-main/main/available_nodes_base64.txt
```

#### 方式2：使用订阅链接
将上面的链接添加到你的代理客户端：
- Clash: 使用 `available_nodes_clash.yaml` 链接
- V2Ray/Shadowrocket: 使用 `available_nodes_base64.txt` 链接

## 📊 工作流程详解

```
┌─────────────────────────────────────────────────────────────┐
│  每6小时第5分钟                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Workflow 1: 订阅收集                                 │  │
│  │  1. 从 Telegram 频道抓取订阅链接                      │  │
│  │  2. 验证链接有效性                                    │  │
│  │  3. 保存到 sub/ 目录                                  │  │
│  │  4. 提交到 GitHub                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓ 25分钟后
┌─────────────────────────────────────────────────────────────┐
│  每6小时第30分钟                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Workflow 2: 节点处理                                 │  │
│  │  1. 拉取最新的订阅链接                                │  │
│  │  2. 下载所有订阅内容（32线程并发）                    │  │
│  │  3. 解析节点（Clash/VMess/SS/Trojan/SSR）            │  │
│  │  4. 第一次筛选：                                      │  │
│  │     ❌ 纯IP节点                                       │  │
│  │     ❌ 80端口                                         │  │
│  │     ❌ 443端口                                        │  │
│  │  5. TCP测速（64线程并发，超时5秒）                   │  │
│  │  6. 第二次筛选：                                      │  │
│  │     ❌ 超时节点                                       │  │
│  │     ❌ 延迟>3000ms                                    │  │
│  │  7. 按延迟排序                                        │  │
│  │  8. 输出 Clash 和 Base64 格式                         │  │
│  │  9. 提交到 GitHub                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## ⚙️ 自定义配置

### 修改筛选规则

编辑 `node_filter.py`:

```python
def filter_node(node):
    # 添加更多端口过滤
    if port in [80, 443, 8080, 8443]:
        return False

    # 添加协议过滤
    if node.get('type') == 'ssr':  # 不要SSR节点
        return False
```

### 修改测速参数

编辑 `node_speedtest.py`:

```python
# 修改超时时间（秒）
def tcp_test(server, port, timeout=3):  # 改为3秒

# 修改延迟阈值（毫秒）
def test_node(node, results, bar):
    if latency > 0 and latency < 2000:  # 改为2000ms
```

### 修改并发数

编辑 `node_speedtest.py`:

```python
# 修改测速并发数
thread_max_num = threading.Semaphore(128)  # 改为128线程
```

编辑 `node_processor.py`:

```python
# 修改下载并发数
thread_max_num = threading.Semaphore(64)  # 改为64线程
```

### 修改运行频率

编辑 `.github/workflows/fetch.yaml`:

```yaml
schedule:
  - cron: '5 */3 * * *'  # 改为每3小时运行
```

编辑 `.github/workflows/process_nodes.yaml`:

```yaml
schedule:
  - cron: '30 */3 * * *'  # 改为每3小时运行
```

## 🔍 故障排查

### 问题1：Actions 运行失败

**原因**：可能是网络问题或订阅链接失效

**解决**：
1. 查看 Actions 日志
2. 手动重新运行 workflow
3. 检查 `config.yaml` 中的 Telegram 频道是否可访问

### 问题2：没有可用节点

**原因**：所有节点都被筛选掉了

**解决**：
1. 放宽筛选条件（允许IP节点或443端口）
2. 增加延迟阈值（改为5000ms）
3. 检查订阅源质量

### 问题3：处理时间过长

**原因**：订阅链接或节点数量太多

**解决**：
1. 减少 `config.yaml` 中的频道数量
2. 降低并发数（避免触发限流）
3. 增加超时时间限制

## 📈 性能优化建议

1. **减少订阅源**：只保留高质量的 Telegram 频道
2. **调整测速参数**：降低超时时间（3秒）和延迟阈值（2000ms）
3. **使用缓存**：GitHub Actions 会自动缓存 pip 依赖
4. **分时运行**：避开高峰期（如凌晨运行）

## 🛡️ 安全建议

1. **不要泄露订阅链接**：输出文件包含真实节点信息
2. **定期更新**：节点会失效，建议每天更新
3. **备份配置**：保存好 `config.yaml` 配置
4. **监控使用**：注意 GitHub Actions 使用配额

## 📞 支持

如有问题，请查看：
- [NODE_PROCESSOR_README.md](NODE_PROCESSOR_README.md) - 技术文档
- [GitHub Issues](https://github.com/你的用户名/collectSub-main/issues) - 提交问题
