import socket
import urllib.request

def get_local_ip():
    """获取局域网 IP"""
    try:
        # 方法1：通过 UDP 连接获取（不需要实际连接）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # 连接公网 DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 方法2：回退到主机名解析
        return socket.gethostbyname(socket.gethostname())

def get_public_ip():
    """获取公网 IP"""
    try:
        # 使用多个服务，提高成功率
        services = [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
        ]
        for url in services:
            try:
                with urllib.request.urlopen(url, timeout=5) as response:
                    return response.read().decode().strip()
            except:
                continue
        return None
    except Exception:
        return None