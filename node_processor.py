import os
import re
import yaml
import base64
import requests
import threading
from loguru import logger
from tqdm import tqdm

from node_filter import (
    parse_clash_nodes, parse_v2ray_nodes, filter_node,
    nodes_to_clash_yaml, nodes_to_base64, is_domain
)
from node_speedtest import batch_test

thread_max_num = threading.Semaphore(32)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
CLASH_OUTPUT = os.path.join(OUTPUT_DIR, 'available_nodes_clash.yaml')
BASE64_OUTPUT = os.path.join(OUTPUT_DIR, 'available_nodes_base64.txt')

SUB_DIR = os.path.join(OUTPUT_DIR, 'sub')
CLASH_SUBS = os.path.join(SUB_DIR, 'sub_all_clash.txt')
LOON_SUBS = os.path.join(SUB_DIR, 'sub_all_loon.txt')
ALL_YAML = os.path.join(SUB_DIR, 'sub_all.yaml')


def load_sub_urls():
    """加载所有订阅链接"""
    urls = set()

    # 从clash订阅文件加载
    for f in [CLASH_SUBS, LOON_SUBS]:
        if os.path.isfile(f):
            with open(f, 'r') as fh:
                for line in fh:
                    line = line.strip()
                    if line and line.startswith('http'):
                        urls.add(line)

    # 从sub_all.yaml加载
    if os.path.isfile(ALL_YAML):
        try:
            with open(ALL_YAML, 'r', encoding='utf-8') as f:
                data = yaml.load(f, Loader=yaml.FullLoader)
            if data:
                for key in ['clash订阅', 'v2订阅', '机场订阅']:
                    items = data.get(key, [])
                    if items:
                        re_str = r"https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]"
                        found = re.findall(re_str, str(items))
                        urls.update(found)
        except:
            pass

    logger.info(f'共加载 {len(urls)} 个订阅链接')
    return list(urls)


def download_sub(url, all_nodes, bar):
    """下载并解析单个订阅"""
    with thread_max_num:
        try:
            headers = {'User-Agent': 'ClashforWindows/0.18.1'}
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                bar.update(1)
                return

            content = resp.text

            # 尝试解析Clash格式
            if 'proxies:' in content:
                nodes = parse_clash_nodes(content)
                all_nodes.extend(nodes)
            else:
                # 尝试Base64格式
                nodes = parse_v2ray_nodes(content)
                all_nodes.extend(nodes)

        except:
            pass
        bar.update(1)


def download_all_subs(urls):
    """批量下载所有订阅"""
    logger.info(f'开始下载订阅，共 {len(urls)} 个')
    all_nodes = []
    bar = tqdm(total=len(urls), desc='下载订阅')

    # 分批处理，每批最多100个线程
    batch_size = 100
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i+batch_size]
        threads = []
        for url in batch:
            t = threading.Thread(target=download_sub, args=(url, all_nodes, bar))
            t.daemon = True
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

    bar.close()
    logger.info(f'下载完成，共获取 {len(all_nodes)} 个节点')
    return all_nodes


def main():
    logger.info('=== 开始节点处理 ===')

    # 1. 加载订阅链接
    urls = load_sub_urls()
    if not urls:
        logger.error('未找到订阅链接')
        return

    # 2. 下载并解析节点
    all_nodes = download_all_subs(urls)
    if not all_nodes:
        logger.error('未获取到任何节点')
        return

    # 3. 去重
    unique_nodes = []
    seen = set()
    for node in all_nodes:
        key = f"{node.get('server')}:{node.get('port')}"
        if key not in seen:
            seen.add(key)
            unique_nodes.append(node)

    logger.info(f'去重后节点数: {len(unique_nodes)}')

    # 4. 测速
    available_nodes = batch_test(unique_nodes)

    if not available_nodes:
        logger.error('没有可用节点')
        return

    # 5. 输出Clash格式
    clash_yaml = nodes_to_clash_yaml(available_nodes)
    with open(CLASH_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(clash_yaml)
    logger.info(f'Clash格式已保存: {CLASH_OUTPUT}')

    # 6. 输出Base64格式
    base64_content = nodes_to_base64(available_nodes)
    with open(BASE64_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(base64_content)
    logger.info(f'Base64格式已保存: {BASE64_OUTPUT}')

    logger.info(f'=== 处理完成，可用节点: {len(available_nodes)} ===')


if __name__ == '__main__':
    main()
