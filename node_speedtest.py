import socket
import threading
from loguru import logger
from tqdm import tqdm

thread_max_num = threading.Semaphore(64)

def tcp_test(server, port, timeout=5):
    """TCP连接测速，返回延迟(ms)，失败返回-1"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        import time
        start = time.time()
        sock.connect((server, int(port)))
        latency = (time.time() - start) * 1000
        sock.close()
        return round(latency, 2)
    except:
        return -1

def test_node(node, results, bar):
    """测试单个节点"""
    with thread_max_num:
        server = node.get('server', '')
        port = node.get('port', 0)

        latency = tcp_test(server, port)
        if latency > 0 and latency < 3000:
            node['latency'] = latency
            results.append(node)

        bar.update(1)

def batch_test(nodes):
    """批量测速节点"""
    if not nodes:
        return []

    logger.info(f'开始测速，共 {len(nodes)} 个节点')
    results = []
    bar = tqdm(total=len(nodes), desc='节点测速')

    batch_size = 200
    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i+batch_size]
        threads = []
        for node in batch:
            t = threading.Thread(target=test_node, args=(node, results, bar))
            t.daemon = True
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    bar.close()

    # 按延迟排序
    results.sort(key=lambda x: x.get('latency', 9999))
    logger.info(f'测速完成，可用节点: {len(results)}/{len(nodes)}')
    return results
