import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

def run_audit(q):
    data = json.dumps({'query': q, 'country': 'IN', 'currency': 'INR', 'language': 'en'}).encode('utf-8')
    req = urllib.request.Request(
        'http://localhost:8000/api/search',
        data=data,
        headers={'Content-Type': 'application/json', 'Connection': 'close'}
    )
    resp = urllib.request.urlopen(req, timeout=30)
    state = json.loads(resp.read().decode('utf-8'))
    print(f"=== Results for: '{q}' ===")
    print("Curated Final Options (Winners):")
    for opt in state['final_options']:
        l = opt['listing']
        print(f"  [{opt['recommendation_tier']}] {l['merchant']} ({l['merchant_domain']}) | Price: {l['base_price']} {l['currency']} | In Stock: {l.get('in_stock')} | Stock Status: {l.get('stock_status')} | URL: {l['listing_url']}")
    
    print("\nComparison Matrix Stock Status of Known Seeds:")
    for row in state['comparison_matrix']:
        if any(d in row['domain'] for d in ['refurbishedpc', 'cashify', 'electronicsbazaar', 'amazon.in', 'newegg']):
            print(f"  {row['merchant']} ({row['domain']}) -> Stock: {row.get('stock_status')} | InStock: {row.get('in_stock')} | URL: {row.get('listing_url')}")

if __name__ == '__main__':
    run_audit('renewed dell latitude 5511 core i7-10850h')
