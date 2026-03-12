#!/usr/bin/env python3
"""测试真实节点解析"""

test_nodes = [
    'vmess://ew0KICAidiI6ICIyIiwNCiAgInBzIjogIummmea4r+S4k+e6vzAzIiwNCiAgImFkZCI6ICJoay5pY2FuZG9pdC5ldS5vcmciLA0KICAicG9ydCI6ICIxMTcyNiIsDQogICJpZCI6ICJiODhiYzAwNC0xNWE5LTQ0ZDYtOTdkOS0xMDg5NTk3YjcwMjAiLA0KICAiYWlkIjogIjAiLA0KICAic2N5IjogImF1dG8iLA0KICAibmV0IjogIndzIiwNCiAgInR5cGUiOiAibm9uZSIsDQogICJob3N0IjogImhrLmljYW5kb2l0LmV1Lm9yZyIsDQogICJwYXRoIjogIi9odW5iIiwNCiAgInRscyI6ICJ0bHMiLA0KICAic25pIjogImhrLmljYW5kb2l0LmV1Lm9yZyIsDQogICJhbHBuIjogIiIsDQogICJmcCI6ICIiLA0KICAiaW5zZWN1cmUiOiAiMCINCn0=',
    'vless://b88bc004-15a9-44d6-97d9-1089597b7020@hk.icandoit.eu.org:18193?encryption=none&security=tls&sni=hk.icandoit.eu.org&fp=chrome&insecure=0&allowInsecure=0&type=ws&host=hk.icandoit.eu.org&path=%2Figaows#%E9%A6%99%E6%B8%AF%E4%B8%93%E7%BA%BF02',
    'trojan://2e4cb968-80ec-4f4e-9c03-be5464dd4ca2@uscc.icandoit.eu.org:16363?security=tls&sni=uscc.icandoit.eu.org&fp=chrome&alpn=http%2F1.1&insecure=0&allowInsecure=0&type=tcp&headerType=none#%E7%BE%8E%E5%9B%BD%E4%B8%93%E7%BA%BF14',
    'hysteria2://1dc9736a-968d-4e46-8170-15c0b9b87601@66.253.5.69:54809?sni=www.bing.com&alpn=h3&insecure=1&allowInsecure=1#%E7%BE%8E%E5%9B%BD09',
    'tuic://1dc9736a-968d-4e46-8170-15c0b9b87601:1dc9736a-968d-4e46-8170-15c0b9b87601@66.253.5.69:63909?sni=www.bing.com&alpn=h3&insecure=1&allowInsecure=1&congestion_control=bbr#%E7%BE%8E%E5%9B%BD13',
    'anytls://b88bc004-15a9-44d6-97d9-1089597b7020@hk.icandoit.eu.org:12218?security=tls&sni=hk.icandoit.eu.org&insecure=0&allowInsecure=0&type=tcp#%E9%A6%99%E6%B8%AF%E4%B8%93%E7%BA%BF10',
    'ss://YWVzLTEyOC1nY206MzU2NWRhMjktOGQ4OC00NjE5LThlNzUtMzc4Zjg0OWE2MDk1@shrimp-door-9527.gym0boy.com:14443#HK-%E9%A6%99%E6%B8%AF-%E5%BF%AB%E9%80%9F%E4%B8%93%E7%BA%BF1',
    'ss://YWVzLTI1Ni1nY206ZmJkZDE5YWMtMmFiNi00MDJmLTkzMzMtN2E1Mzc3YjM2NjJj@fcjgrg.hotssid.com:10702#%F0%9F%87%A8%F0%9F%87%B3%2B%E5%8F%B0%E6%B9%BE%2B03',
    'trojan://94566b52-e572-454a-9533-9350a18de2c4@lt-sin.ltdns.top:27044?security=tls&sni=www.ithome.com&insecure=1&allowInsecure=1&type=tcp&headerType=none#%5B%E6%A0%B8%E5%BF%83%5D%2B%E6%96%B0%E5%8A%A0%E5%9D%A1%2B03',
]

if __name__ == '__main__':
    from node_filter import parse_single_node, nodes_to_clash_yaml
    import yaml
    import json

    print('=' * 80)
    print('测试所有协议节点解析')
    print('=' * 80)

    parsed_nodes = []
    for i, uri in enumerate(test_nodes, 1):
        protocol = uri.split('://')[0]
        print(f'\n节点 {i} [{protocol}]: {uri[:50]}...')
        node = parse_single_node(uri)
        if node:
            print(f'✅ 解析成功')
            print(f'   类型: {node.get("type")}')
            print(f'   名称: {node.get("name")}')
            print(f'   服务器: {node.get("server")}:{node.get("port")}')
            print(f'   字段数: {len(node)}')
            parsed_nodes.append(node)
        else:
            print(f'❌ 解析失败')

    print('\n' + '=' * 80)
    print(f'解析成功: {len(parsed_nodes)}/{len(test_nodes)}')
    print('=' * 80)

    if parsed_nodes:
        print('\n生成 Clash YAML:')
        print('-' * 80)
        clash_yaml = nodes_to_clash_yaml(parsed_nodes)
        print(clash_yaml)

        print('\n验证 YAML 格式:')
        try:
            data = yaml.safe_load(clash_yaml)
            proxies = data.get('proxies', [])
            print(f'✅ YAML 格式正确，包含 {len(proxies)} 个节点')

            # 统计协议类型
            types = {}
            for p in proxies:
                t = p.get('type', 'unknown')
                types[t] = types.get(t, 0) + 1

            print(f'\n协议统计:')
            for t, count in sorted(types.items()):
                print(f'  {t}: {count}个')

        except Exception as e:
            print(f'❌ YAML 格式错误: {e}')

