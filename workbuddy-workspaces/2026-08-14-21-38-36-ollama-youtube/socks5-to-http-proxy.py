import socket
import threading
import socks

SOCKS5_HOST = '127.0.0.1'
SOCKS5_PORT = 10808
HTTP_LISTEN = ('127.0.0.1', 18080)


def handle_client(client):
    try:
        client.settimeout(60)
        data = b''
        while b'\r\n\r\n' not in data:
            chunk = client.recv(4096)
            if not chunk:
                client.close()
                return
            data += chunk
        first_line = data.split(b'\r\n', 1)[0].decode('latin-1')
        parts = first_line.split(' ')
        if len(parts) < 2:
            client.close()
            return
        method, target = parts[0], parts[1]

        if method == 'CONNECT':
            host, port = target.split(':')
            port = int(port)
        else:
            t = target.replace('http://', '').replace('https://', '')
            if '/' in t:
                host_port = t.split('/', 1)[0]
            else:
                host_port = t
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 80

        remote = socks.socksocket()
        remote.set_proxy(socks.SOCKS5, SOCKS5_HOST, SOCKS5_PORT, rdns=True)
        remote.settimeout(60)
        remote.connect((host, port))

        if method == 'CONNECT':
            client.sendall(b'HTTP/1.1 200 Connection established\r\n\r\n')
        else:
            remote.sendall(data)

        def pipe(src, dst):
            try:
                while True:
                    buf = src.recv(8192)
                    if not buf:
                        break
                    dst.sendall(buf)
            except Exception:
                pass
            finally:
                try: src.close()
                except: pass
                try: dst.close()
                except: pass

        t1 = threading.Thread(target=pipe, args=(client, remote), daemon=True)
        t2 = threading.Thread(target=pipe, args=(remote, client), daemon=True)
        t1.start(); t2.start()
        t1.join(); t2.join()
    except Exception as e:
        try:
            client.sendall(f'HTTP/1.1 502 Bad Gateway\r\n\r\n{e}'.encode())
        except Exception:
            pass
        try:
            client.close()
        except Exception:
            pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(HTTP_LISTEN)
    server.listen(128)
    print(f'HTTP proxy listening on {HTTP_LISTEN[0]}:{HTTP_LISTEN[1]} -> SOCKS5 {SOCKS5_HOST}:{SOCKS5_PORT}', flush=True)
    while True:
        client, addr = server.accept()
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()


if __name__ == '__main__':
    main()
