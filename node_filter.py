import re
import json
import yaml
import base64
from urllib.parse import urlparse, parse_qs, unquote
from loguru import logger

# IPv4 和 IPv6 正则
_IPV4 = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
_IPV6 = re.compile(r'^[0-9a-fA-F:]+$')

def is_domain(server):
    """检查是否为域名（非纯IP）"""
    if not server:
        return False
    server = server.strip('[]')
    if _IPV4.match(server):
        return False
    if _IPV6.match(server):
        return False
    return True

def filter_node(node):
    """筛选节点：只保留域名节点，排除80/443端口"""
    if not isinstance(node, dict):
        return False

    server = str(node.get('server', '')).strip()
    port = int(node.get('port', 0))

    if not server:
        return False

    # 排除纯IP
    if not is_domain(server):
        return False

    # 排除80和443端口
    if port in [80, 443]:
        return False

    return True

def parse_clash_nodes(yaml_content):
    """解析Clash YAML格式节点 - 完整保留所有字段"""
    try:
        data = yaml.safe_load(yaml_content)
        if not data:
            return []

        proxies = data.get('proxies', [])
        # 完整保留节点，只做筛选
        return [node for node in proxies if filter_node(node)]
    except Exception as e:
        logger.debug(f'解析Clash YAML失败: {e}')
        return []

def _b64_decode(s):
    """Base64解码，自动补齐padding"""
    s = s.strip()
    padding = 4 - len(s) % 4
    if padding != 4:
        s += '=' * padding
    try:
        return base64.urlsafe_b64decode(s).decode('utf-8')
    except:
        return base64.b64decode(s).decode('utf-8')

def parse_v2ray_nodes(base64_content):
    """解析Base64格式节点"""
    nodes = []
    try:
        decoded = _b64_decode(base64_content)
        lines = decoded.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            node = parse_single_node(line)
            if node and filter_node(node):
                nodes.append(node)
    except Exception as e:
        logger.debug(f'解析Base64失败: {e}')

    return nodes

def parse_single_node(uri):
    """解析单个节点URI"""
    try:
        if uri.startswith('vmess://'):
            return parse_vmess(uri)
        elif uri.startswith('vless://'):
            return parse_vless(uri)
        elif uri.startswith('ss://'):
            return parse_ss(uri)
        elif uri.startswith('trojan://'):
            return parse_trojan(uri)
        elif uri.startswith('ssr://'):
            return parse_ssr(uri)
        elif uri.startswith('hysteria://') or uri.startswith('hysteria2://') or uri.startswith('hy2://'):
            return parse_hysteria(uri)
        elif uri.startswith('tuic://'):
            return parse_tuic(uri)
        # anytls 通常是 vless 的别名
        elif uri.startswith('anytls://'):
            return parse_vless(uri.replace('anytls://', 'vless://'))
    except Exception as e:
        logger.debug(f'解析节点失败: {e}')
    return None

def parse_vmess(uri):
    """解析VMess节点 - 转为Clash格式"""
    try:
        data = base64.b64decode(uri[8:]).decode('utf-8')
        config = json.loads(data)

        node = {
            'name': config.get('ps', 'VMess'),
            'type': 'vmess',
            'server': config.get('add', ''),
            'port': int(config.get('port', 0)),
            'uuid': config.get('id', ''),
            'alterId': int(config.get('aid', 0)),
            'cipher': config.get('scy', 'auto'),
            'udp': True
        }

        # 传输层配置
        net = config.get('net', 'tcp')
        if net != 'tcp':
            node['network'] = net

        if net == 'ws':
            node['ws-opts'] = {
                'path': config.get('path', '/'),
                'headers': {'Host': config.get('host', '')} if config.get('host') else {}
            }
        elif net == 'grpc':
            node['grpc-opts'] = {
                'grpc-service-name': config.get('path', '')
            }
        elif net == 'h2':
            node['h2-opts'] = {
                'path': config.get('path', '/'),
                'host': [config.get('host', '')]
            }

        # TLS配置
        tls = config.get('tls', '')
        if tls:
            node['tls'] = True
            if config.get('sni'):
                node['sni'] = config.get('sni')
            node['skip-cert-verify'] = config.get('skip-cert-verify', False)

        return node
    except Exception as e:
        logger.debug(f'解析VMess失败: {e}')
        return None

def parse_vless(uri):
    """解析VLESS节点 - 转为Clash格式"""
    try:
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        node = {
            'name': unquote(parsed.fragment) or 'VLESS',
            'type': 'vless',
            'server': parsed.hostname,
            'port': parsed.port or 443,
            'uuid': parsed.username,
            'udp': True
        }

        # 传输层
        flow = params.get('flow', [''])[0]
        if flow:
            node['flow'] = flow

        network = params.get('type', ['tcp'])[0]
        if network != 'tcp':
            node['network'] = network

        if network == 'ws':
            node['ws-opts'] = {
                'path': params.get('path', ['/'])[0],
                'headers': {'Host': params.get('host', [''])[0]} if params.get('host') else {}
            }
        elif network == 'grpc':
            node['grpc-opts'] = {
                'grpc-service-name': params.get('serviceName', [''])[0]
            }

        # TLS/Reality
        security = params.get('security', [''])[0]
        if security == 'tls':
            node['tls'] = True
            if params.get('sni'):
                node['sni'] = params.get('sni', [''])[0]
            node['skip-cert-verify'] = params.get('allowInsecure', ['0'])[0] == '1'
        elif security == 'reality':
            node['tls'] = True
            node['reality-opts'] = {
                'public-key': params.get('pbk', [''])[0],
                'short-id': params.get('sid', [''])[0]
            }
            if params.get('sni'):
                node['sni'] = params.get('sni', [''])[0]

        return node
    except Exception as e:
        logger.debug(f'解析VLESS失败: {e}')
        return None

def parse_ss(uri):
    """解析Shadowsocks节点（支持SIP002和legacy格式）- 转为Clash格式"""
    try:
        rest = uri[5:]
        fragment = ''
        if '#' in rest:
            rest, fragment = rest.rsplit('#', 1)
            fragment = unquote(fragment)

        # SIP002格式: ss://base64(method:password)@server:port
        if '@' in rest:
            userinfo, server_port = rest.rsplit('@', 1)
            try:
                decoded = _b64_decode(userinfo)
                method, password = decoded.split(':', 1)
            except:
                method, password = userinfo.split(':', 1)
            server, port = server_port.rsplit(':', 1)
            port = port.split('?')[0].split('/')[0]

            # 解析插件
            plugin = None
            plugin_opts = {}
            if '?' in server_port:
                query = server_port.split('?', 1)[1]
                params = parse_qs(query)
                if 'plugin' in params:
                    plugin_str = params['plugin'][0]
                    if ';' in plugin_str:
                        plugin, opts_str = plugin_str.split(';', 1)
                        for opt in opts_str.split(';'):
                            if '=' in opt:
                                k, v = opt.split('=', 1)
                                plugin_opts[k] = v
                    else:
                        plugin = plugin_str
        else:
            # legacy格式
            decoded = _b64_decode(rest)
            method, rest2 = decoded.split(':', 1)
            password, server_port = rest2.rsplit('@', 1)
            server, port = server_port.rsplit(':', 1)
            plugin = None
            plugin_opts = {}

        node = {
            'name': fragment or 'SS',
            'type': 'ss',
            'server': server.strip(),
            'port': int(port.strip()),
            'cipher': method.strip(),
            'password': password,
            'udp': True
        }

        # 插件配置
        if plugin:
            if 'obfs' in plugin:
                node['plugin'] = 'obfs'
                node['plugin-opts'] = {
                    'mode': plugin_opts.get('obfs', 'http'),
                    'host': plugin_opts.get('obfs-host', '')
                }
            elif 'v2ray' in plugin:
                node['plugin'] = 'v2ray-plugin'
                node['plugin-opts'] = {
                    'mode': plugin_opts.get('mode', 'websocket'),
                    'host': plugin_opts.get('host', ''),
                    'path': plugin_opts.get('path', '/'),
                    'tls': plugin_opts.get('tls', '') == 'true'
                }

        return node
    except Exception as e:
        logger.debug(f'解析SS失败: {e}')
        return None

def parse_trojan(uri):
    """解析Trojan节点 - 转为Clash格式"""
    try:
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        node = {
            'name': unquote(parsed.fragment) or 'Trojan',
            'type': 'trojan',
            'server': parsed.hostname,
            'port': parsed.port or 443,
            'password': parsed.username,
            'udp': True
        }

        # 传输层
        network = params.get('type', ['tcp'])[0]
        if network != 'tcp':
            node['network'] = network

        if network == 'ws':
            node['ws-opts'] = {
                'path': params.get('path', ['/'])[0],
                'headers': {'Host': params.get('host', [''])[0]} if params.get('host') else {}
            }
        elif network == 'grpc':
            node['grpc-opts'] = {
                'grpc-service-name': params.get('serviceName', [''])[0]
            }

        # TLS
        if params.get('sni'):
            node['sni'] = params.get('sni', [''])[0]
        node['skip-cert-verify'] = params.get('allowInsecure', ['0'])[0] == '1'

        return node
    except Exception as e:
        logger.debug(f'解析Trojan失败: {e}')
        return None

def parse_ssr(uri):
    """解析SSR节点 - 转为Clash格式"""
    try:
        decoded = _b64_decode(uri[6:])
        # SSR格式: server:port:protocol:method:obfs:password_base64/?params
        parts = decoded.split('/')
        main = parts[0]
        params = parse_qs(parts[1][1:]) if len(parts) > 1 else {}

        server, port, protocol, method, obfs, password_b64 = main.split(':')
        password = _b64_decode(password_b64)

        node = {
            'name': _b64_decode(params.get('remarks', ['SSR'])[0]) if params.get('remarks') else 'SSR',
            'type': 'ssr',
            'server': server,
            'port': int(port),
            'cipher': method,
            'password': password,
            'protocol': protocol,
            'obfs': obfs,
            'udp': True
        }

        if params.get('obfsparam'):
            node['obfs-param'] = _b64_decode(params['obfsparam'][0])
        if params.get('protoparam'):
            node['protocol-param'] = _b64_decode(params['protoparam'][0])

        return node
    except Exception as e:
        logger.debug(f'解析SSR失败: {e}')
        return None

def parse_hysteria(uri):
    """解析Hysteria/Hysteria2节点 - 转为Clash格式"""
    try:
        if uri.startswith('hysteria2://') or uri.startswith('hy2://'):
            ptype = 'hysteria2'
            uri = uri.replace('hy2://', 'hysteria2://')
        else:
            ptype = 'hysteria'

        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        node = {
            'name': unquote(parsed.fragment) or ptype.upper(),
            'type': ptype,
            'server': parsed.hostname,
            'port': parsed.port or 443,
            'password': parsed.username or params.get('auth', [''])[0],
            'udp': True
        }

        if params.get('sni'):
            node['sni'] = params['sni'][0]
        if params.get('obfs'):
            node['obfs'] = params['obfs'][0]
        if params.get('alpn'):
            node['alpn'] = params['alpn'][0].split(',')

        node['skip-cert-verify'] = params.get('insecure', ['0'])[0] == '1'

        return node
    except Exception as e:
        logger.debug(f'解析Hysteria失败: {e}')
        return None

def parse_tuic(uri):
    """解析TUIC节点 - 转为Clash格式"""
    try:
        parsed = urlparse(uri)
        params = parse_qs(parsed.query)

        # TUIC格式: tuic://uuid:password@server:port
        uuid_password = parsed.username
        if ':' in uuid_password:
            uuid, password = uuid_password.split(':', 1)
        else:
            uuid = uuid_password
            password = uuid_password

        node = {
            'name': unquote(parsed.fragment) or 'TUIC',
            'type': 'tuic',
            'server': parsed.hostname,
            'port': parsed.port or 443,
            'uuid': uuid,
            'password': password,
            'udp': True
        }

        if params.get('sni'):
            node['sni'] = params['sni'][0]
        if params.get('alpn'):
            node['alpn'] = params['alpn'][0].split(',')
        if params.get('congestion_control'):
            node['congestion-control'] = params['congestion_control'][0]

        node['skip-cert-verify'] = params.get('insecure', ['0'])[0] == '1'

        return node
    except Exception as e:
        logger.debug(f'解析TUIC失败: {e}')
        return None

def nodes_to_clash_yaml(nodes):
    """节点转Clash YAML格式 - 完整保留所有字段"""
    clean_nodes = []
    for node in nodes:
        # 只移除内部元数据字段
        n = {k: v for k, v in node.items() if k not in ['latency']}
        clean_nodes.append(n)

    return yaml.dump({'proxies': clean_nodes}, allow_unicode=True, default_flow_style=False, sort_keys=False)

def nodes_to_base64(nodes):
    """节点转Base64格式"""
    lines = []
    for node in nodes:
        uri = node_to_uri(node)
        if uri:
            lines.append(uri)

    content = '\n'.join(lines)
    return base64.b64encode(content.encode('utf-8')).decode('utf-8')

def node_to_uri(node):
    """节点转URI - 支持多种协议"""
    node_type = node.get('type', '')

    if node_type == 'vmess':
        return vmess_to_uri(node)
    elif node_type == 'vless':
        return vless_to_uri(node)
    elif node_type == 'ss':
        return ss_to_uri(node)
    elif node_type == 'trojan':
        return trojan_to_uri(node)
    elif node_type == 'ssr':
        return ssr_to_uri(node)
    elif node_type in ['hysteria', 'hysteria2']:
        return hysteria_to_uri(node)
    elif node_type == 'tuic':
        return tuic_to_uri(node)

    return None

def vmess_to_uri(node):
    """VMess节点转URI"""
    try:
        config = {
            'v': '2',
            'ps': node.get('name', ''),
            'add': node.get('server', ''),
            'port': str(node.get('port', '')),
            'id': node.get('uuid', ''),
            'aid': str(node.get('alterId', 0)),
            'scy': node.get('cipher', 'auto'),
            'net': node.get('network', 'tcp'),
            'type': 'none',
            'tls': 'tls' if node.get('tls') else ''
        }

        if node.get('sni'):
            config['sni'] = node['sni']

        if node.get('ws-opts'):
            config['path'] = node['ws-opts'].get('path', '/')
            config['host'] = node['ws-opts'].get('headers', {}).get('Host', '')

        json_str = json.dumps(config, ensure_ascii=False)
        return 'vmess://' + base64.b64encode(json_str.encode()).decode()
    except:
        return None

def vless_to_uri(node):
    """VLESS节点转URI"""
    try:
        server = node.get('server', '')
        port = node.get('port', 443)
        uuid = node.get('uuid', '')
        name = node.get('name', '')

        params = []
        if node.get('network'):
            params.append(f"type={node['network']}")
        if node.get('flow'):
            params.append(f"flow={node['flow']}")
        if node.get('sni'):
            params.append(f"sni={node['sni']}")
        if node.get('tls'):
            params.append("security=tls")

        query = '&'.join(params)
        return f"vless://{uuid}@{server}:{port}?{query}#{name}"
    except:
        return None

def ss_to_uri(node):
    """SS节点转URI"""
    try:
        method = node.get('cipher', '')
        password = node.get('password', '')
        server = node.get('server', '')
        port = node.get('port', '')
        name = node.get('name', '')

        userinfo = f"{method}:{password}"
        encoded = base64.urlsafe_b64encode(userinfo.encode()).decode().rstrip('=')

        # 插件
        plugin_str = ''
        if node.get('plugin'):
            plugin_str = f"?plugin={node['plugin']}"
            if node.get('plugin-opts'):
                opts = node['plugin-opts']
                plugin_str += ';' + ';'.join([f"{k}={v}" for k, v in opts.items()])

        return f"ss://{encoded}@{server}:{port}{plugin_str}#{name}"
    except:
        return None

def trojan_to_uri(node):
    """Trojan节点转URI"""
    try:
        password = node.get('password', '')
        server = node.get('server', '')
        port = node.get('port', 443)
        name = node.get('name', '')

        params = []
        if node.get('sni'):
            params.append(f"sni={node['sni']}")
        if node.get('network'):
            params.append(f"type={node['network']}")

        query = '&'.join(params)
        return f"trojan://{password}@{server}:{port}?{query}#{name}"
    except:
        return None

def ssr_to_uri(node):
    """SSR节点转URI"""
    try:
        server = node.get('server', '')
        port = node.get('port', '')
        protocol = node.get('protocol', '')
        method = node.get('cipher', '')
        obfs = node.get('obfs', '')
        password = node.get('password', '')
        name = node.get('name', 'SSR')

        password_b64 = base64.urlsafe_b64encode(password.encode()).decode().rstrip('=')
        main = f"{server}:{port}:{protocol}:{method}:{obfs}:{password_b64}"

        params = []
        params.append(f"remarks={base64.urlsafe_b64encode(name.encode()).decode().rstrip('=')}")

        param_str = '&'.join(params)
        full = f"{main}/?{param_str}"
        encoded = base64.urlsafe_b64encode(full.encode()).decode().rstrip('=')

        return f"ssr://{encoded}"
    except:
        return None

def hysteria_to_uri(node):
    """Hysteria节点转URI"""
    try:
        ptype = node.get('type', 'hysteria')
        server = node.get('server', '')
        port = node.get('port', 443)
        password = node.get('password', '')
        name = node.get('name', '')

        params = []
        if node.get('sni'):
            params.append(f"sni={node['sni']}")
        if node.get('obfs'):
            params.append(f"obfs={node['obfs']}")

        query = '&'.join(params)
        prefix = 'hy2' if ptype == 'hysteria2' else 'hysteria'
        return f"{prefix}://{password}@{server}:{port}?{query}#{name}"
    except:
        return None

def tuic_to_uri(node):
    """TUIC节点转URI"""
    try:
        server = node.get('server', '')
        port = node.get('port', 443)
        uuid = node.get('uuid', '')
        password = node.get('password', '')
        name = node.get('name', '')

        params = []
        if node.get('sni'):
            params.append(f"sni={node['sni']}")
        if node.get('alpn'):
            alpn = ','.join(node['alpn']) if isinstance(node['alpn'], list) else node['alpn']
            params.append(f"alpn={alpn}")
        if node.get('congestion-control'):
            params.append(f"congestion_control={node['congestion-control']}")

        query = '&'.join(params)
        return f"tuic://{uuid}:{password}@{server}:{port}?{query}#{name}"
    except:
        return None
