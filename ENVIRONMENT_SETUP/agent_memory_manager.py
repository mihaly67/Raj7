import os
import sys
import json
import argparse
import datetime
import subprocess

# Kiderítjük, hogy melyik repóban futunk
repo_name = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Knowledge_Base', f'agent_memory_{repo_name}.jsonl')

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
            f.write(json.dumps(entry) + '\n')
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
        f.write(json.dumps(entry) + '\n')
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
    output = '🧠 === AGENT HOSSZÚTÁVÚ MEMÓRIA === 🧠\n'
    total_chars = 0
    for idx, entry in enumerate(entries, 1):
        cat = entry.get('category', 'Általános')
        cont = entry.get('content', '')
        if cat == 'SESSION_MARKER':
            output += f'[{idx}] {entry.get("timestamp", "")[:19]} | 🛑 {cont} 🛑\n'
        else:
            output += f'[{idx}] {entry.get("timestamp", "")[:10]} | Téma: {cat}\n    Tartalom: {cont}\n'
        output += '-' * 50 + '\n'
        total_chars += len(cont)
    return output

def do_sync():
    print('🤖 [Kontextus Titkár] Lokális memória VPS felhő-szinkronizáció indítása...')
    try:
        bridge_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools', 'skills', 'mcp_bridge_tool.py')
        if not os.path.exists(bridge_script):
            print('⚠️ mcp_bridge_tool.py nem található, kihagyom az MCP szinkronizációt.')
            return
            
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Call the remote MCP server to save this memory under the repo's specific memory file
        subprocess.run([sys.executable, bridge_script, 'execute_bash', f"mkdir -p ~/Jules_mx/memory_offload && cat << 'INNER_EOF' > ~/Jules_mx/memory_offload/backup_{repo_name}.jsonl\n{content}\nINNER_EOF"], check=False)
        print('✅ Lokális memória sikeresen felszinkronizálva a VPS-re.')
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
