import socket
import threading
import urllib.request
import json
import time

def start_clean_relay(proxy_port, target_port):
    def handle_client(client_sock):
        try:
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.connect(('127.0.0.1', target_port))
            e1 = threading.Event()
            e2 = threading.Event()
            def pipe(src, dst, ev):
                try:
                    while True:
                        d = src.recv(16384)
                        if not d:
                            break
                        dst.sendall(d)
                except Exception:
                    pass
                finally:
                    try:
                        dst.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass
                    ev.set()

            threading.Thread(target=pipe, args=(client_sock, target, e1), daemon=True).start()
            threading.Thread(target=pipe, args=(target, client_sock, e2), daemon=True).start()
            def cleanup():
                e1.wait(timeout=30)
                e2.wait(timeout=30)
                try: client_sock.close()
                except Exception: pass
                try: target.close()
                except Exception: pass
            threading.Thread(target=cleanup, daemon=True).start()
        except Exception:
            try: client_sock.close()
            except Exception: pass

    srv = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('::1', proxy_port))
    srv.listen(50)
    def loop():
        while True:
            c, _ = srv.accept()
            threading.Thread(target=handle_client, args=(c,), daemon=True).start()
    threading.Thread(target=loop, daemon=True).start()

if __name__ == '__main__':
    start_clean_relay(8889, 8000)
    time.sleep(0.5)

    q = 'Samsung Galaxy A17'
    data = json.dumps({'query': q, 'country': 'IN', 'currency': 'INR', 'language': 'en'}).encode('utf-8')
    req = urllib.request.Request('http://[::1]:8889/api/search', data=data, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=15)
    state = json.loads(resp.read().decode('utf-8'))
    print("SUCCESS! Options count:", len(state['final_options']))
    for opt in state['final_options']:
        l = opt['listing']
        print(f"  [{opt['recommendation_tier']}] {l['merchant']} ({l['merchant_domain']}) -> URL: {l['listing_url']}")
