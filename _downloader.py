"""统一下载工具 - 代理/镜像/进度条/超时重试/SSL处理"""
import subprocess, os, json

ARIA2C = r"C:\Users\cxx\WorkBuddy\Claw\tools\aria2c.exe"

def download(url, output_dir, filename=None, timeout=30, retries=3, proxy="http://127.0.0.1:7890", no_proxy=False):
    """下载文件(自动代理+进度条+超时重试+SSL处理)
    
    Args:
        url: 下载链接
        output_dir: 输出目录
        filename: 文件名(默认从URL提取)
        timeout: 超时秒数
        retries: 重试次数
        proxy: 代理地址
        no_proxy: 强制无代理
    """
    if filename is None:
        filename = url.rstrip("/").split("/")[-1].split("?")[0]
    
    os.makedirs(output_dir, exist_ok=True)
    fpath = os.path.join(output_dir, filename)
    
    strategies = []
    if not no_proxy:
        strategies.append(("proxy", proxy))
    strategies.append(("direct", ""))
    
    for mode, proxy_addr in strategies:
        cmd = [
            ARIA2C, "-x", "8", "-s", "8",
            "--timeout", "15",
            "--connect-timeout", "10",
            "--max-tries", str(retries),
            "--retry-wait", "3",
            "--console-log-level", "notice",
            "--summary-interval", "1",
            "-d", output_dir, "-o", filename, url
        ]
        if proxy_addr:
            cmd.insert(2, "--all-proxy=" + proxy_addr)
        
        desc = "代理" if mode == "proxy" else "直连"
        proc = subprocess.run(cmd, capture_output=True, text=True)
        
        if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
            return fpath
        
        # aria2c返回3=资源不存在, 不用再试
        if proc.returncode == 3:
            break
    
    return None


def github_raw(repo, filepath, output_dir, filename=None):
    """下载GitHub raw文件(自动走代理/直连双策略)"""
    url = f"https://raw.githubusercontent.com/{repo}/main/{filepath}"
    
    # 先试代理
    result = download(url, output_dir, filename, proxy="http://127.0.0.1:7890")
    if result:
        return result
    
    # 代理失败 - 试ghfast镜像
    url2 = f"https://ghfast.top/https://raw.githubusercontent.com/{repo}/main/{filepath}"
    result = download(url2, output_dir, filename, no_proxy=True)
    if result:
        return result
    
    # 镜像也失败 - 试直连
    url3 = f"https://raw.githubusercontent.com/{repo}/main/{filepath}"
    result = download(url3, output_dir, filename, no_proxy=True)
    if result:
        return result
    
    return None


def test_connection():
    """测试网络连通性"""
    import requests
    results = {}
    
    # 测国内
    try:
        r = requests.get("https://www.baidu.com", timeout=5)
        results["国内直连"] = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        results["国内直连"] = str(e)[:50]
    
    # 测代理
    try:
        r = requests.get("https://www.google.com", 
            proxies={"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"},
            timeout=5)
        results["代理Google"] = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        results["代理Google"] = str(e)[:50]
    
    # 测GitHub代理
    try:
        r = requests.get("https://github.com",
            proxies={"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"},
            timeout=5)
        results["代理GitHub"] = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        results["代理GitHub"] = str(e)[:50]
    
    for k, v in results.items():
        print(f"  [{v[:4]}] {k}")
    
    return results


if __name__ == "__main__":
    print("=== 网络诊断 ===")
    test_connection()
