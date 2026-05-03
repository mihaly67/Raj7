import os
import sys
import json
import argparse
import datetime
import subprocess

# A lokális fájlnévnek agent_memory.jsonl-nek KELL lennie a rendszer többi scriptje miatt.
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Knowledge_Base', 'agent_memory.jsonl')

def get_repo_name():
    # Megpróbáljuk git confignól
    try:
        url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if url:
            # git@github.com:mihaly67/raj1.git -> raj1
            name = url.split('/')[-1].replace('.git', '')
            return name
    except:
        pass
    # Fallback mappa névből
    return os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def init_memory_file():
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            pass
        print(f'✅ Memória fájl inicializálva: {MEMORY_FILE}')

def write_memory(category: str, content: str):
    init_memory_file()
    entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'category': category,
        'content': content
    }
    try:
        with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '
')
            f.flush()
            os.fsync(f.fileno())
        print(f'🧠 Memória elmentve a lemezre: {category}')
    except Exception as e:
        print(f'❌ Kritikus hiba a memória mentésekor: {e}')

def mark_session(event: str):
    init_memory_file()
    timestamp = datetime.datetime.now().isoformat()
    entry = {'timestamp': timestamp, 'category': 'SESSION_MARKER', 'content': event}
    with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + '
')
    print(f'🔄 Session marker bejegyezve: {event}')

def read_memory(limit: int = 10, category_filter: str = None):
    import time
    start_time = time.time()
    init_memory_file()
    results = []
    try:
         with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines):
                if not line.strip(): continue
                try:
                    entry = json.loads(line)
                    if category_filter and entry.get('category') != category_filter:
                        continue
                    results.append(entry)
                    if len(results) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
         print(f'Hiba a memória olvasásakor: {e}')
         return None, 0.0
    return results, time.time() - start_time

def format_memory_for_agent(entries, exec_time=None):
    if not entries:
        return 'A memória jelenleg üres.'
    output = '🧠 === AGENT HOSSZÚTÁVÚ MEMÓRIA === 🧠
'
    total_chars = 0
    for idx, entry in enumerate(entries, 1):
        cat = entry.get('category', 'Általános')
        cont = entry.get('content', '')
        if cat == 'SESSION_MARKER':
            output += f'[{idx}] {entry.get("timestamp", "")[:19]} | 🛑 {cont} 🛑
'
        else:
            output += f'[{idx}] {entry.get("timestamp", "")[:10]} | Téma: {cat}
    Tartalom: {cont}
'
        output += '-' * 50 + '
'
        total_chars += len(cont)
    return output

def do_sync():
    print('🤖 [Kontextus Titkár] Lokális memória VPS felhő-szinkronizáció indítása...')
    try:
        vps_bridge = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools', 'vps_bridge.py')
        if not os.path.exists(vps_bridge):
            print('⚠️ vps_bridge.py nem található, kihagyom az SFTP szinkronizációt.')
            return
            
        repo_name = get_repo_name()
        vps_target = f"/home/misi/Jules_mx/memory_offload/backup_{repo_name}.jsonl"
        
        # Mappa letrehozasa a szerveren
        subprocess.run([sys.executable, vps_bridge, "mkdir -p /home/misi/Jules_mx/memory_offload"], check=False, stdout=subprocess.DEVNULL)
        
        # Fajl feltoltese upload moddal az escape anomaliak elkerulese erdekeben
        subprocess.run([sys.executable, vps_bridge, "--upload", MEMORY_FILE, vps_target], check=False, stdout=subprocess.DEVNULL)
        
        print('✅ Lokális memória sikeresen felszinkronizálva a VPS-re (Izolált formában).')
    except Exception as e:
        print(f'⚠️ Hiba a memória szinkronizációjakor: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', choices=['write', 'read', 'start_session', 'end_session', 'sync'], required=True)
    parser.add_argument('--category', type=str, default='General')
    parser.add_argument('--content', type=str)
    parser.add_argument('--limit', type=int, default=5)

    args = parser.parse_args()

    if args.action == 'write':
        write_memory(args.category, args.content)
        do_sync()
    elif args.action == 'sync':
        do_sync()
    elif args.action == 'start_session':
        mark_session('[SESSION_START]')
        do_sync()
    elif args.action == 'end_session':
        mark_session('[SESSION_END]')
        do_sync()
    elif args.action == 'read':
        entries, exec_time = read_memory(limit=args.limit, category_filter=args.category if args.category != 'General' else None)
        print(format_memory_for_agent(entries, exec_time))
