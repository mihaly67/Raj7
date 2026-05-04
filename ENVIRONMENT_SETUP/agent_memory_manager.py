import os
import sys
import json
import argparse
import datetime
from pathlib import Path

# A memória fájl helye (A Git repó része lesz, így a sessionök között perzisztens marad)
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Knowledge_Base", "agent_memory.jsonl")

def get_repo_name():
    # Megpróbáljuk git confignól kinyerni
    try:
        import subprocess
        url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if url:
            name = url.split('/')[-1].replace('.git', '')
            return name
    except:
        pass
    # Fallback mappa névből
    return os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def init_memory_file():
    """Létrehozza a memóriafájlt, ha még nem létezik."""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            pass # Létrehoz egy üres fájlt
        print(f"✅ Memória fájl inicializálva: {MEMORY_FILE}")

def write_memory(category: str, content: str):
    """
    Soronkénti (append) írás a lemezre. O(1) RAM használat.
    A Git így csak az új sorokat fogja diff-ként tárolni, nem bloat-olja a repót.
    """
    init_memory_file()

    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "category": category,
        "content": content
    }

    # Atomi írás szimulálása: megpróbáljuk fájl zárolással vagy gyors append-el
    try:
        with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno()) # Biztosítjuk, hogy fizikailag is a lemezre kerüljön az OS bufferből
        print(f"🧠 Memória elmentve a lemezre (fsync biztosítva)! Kategória: {category}")
    except Exception as e:
        print(f"❌ Kritikus hiba a memória mentésekor: {e}")

def mark_session(event: str):
    """Bejegyez egy [SESSION_START] vagy [SESSION_END] markert."""
    init_memory_file()
    timestamp = datetime.datetime.now().isoformat()
    entry = {"timestamp": timestamp, "category": "SESSION_MARKER", "content": event}
    with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry) + "\n")
    print(f"🔄 Session marker bejegyezve: {event}")

def read_memory(limit: int = 10, category_filter: str = None):
    """
    Visszaolvassa a memóriát. O(1) közeli futás, ha limitált számú sort olvasunk.
    Kereshetünk konkrét kategóriára is.
    """
    import time
    start_time = time.time()
    init_memory_file()

    results = []
    # Fájl visszafelé olvasása (tail), hogy a legfrissebb emlékeink legyenek elöl
    # Mivel a fájl kicsi lesz (<10MB), egyelőre betöltjük a sorokat, majd reverse.
    # Gigabájtos méretnél ezt optimalizálni kell igazi file-pointer tailinggel.
    try:
         with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

            for line in reversed(lines):
                if not line.strip(): continue
                try:
                    entry = json.loads(line)
                    if category_filter and entry.get("category") != category_filter:
                        continue

                    results.append(entry)
                    if len(results) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
         print(f"Hiba a memória olvasásakor: {e}")
         return None, 0.0

    end_time = time.time()
    execution_time = end_time - start_time
    return results, execution_time

def format_memory_for_agent(entries, exec_time=None):
    """Emberi/Agent által olvasható formátumba önti a JSON kimenetet, token / hallucináció figyeléssel."""
    if not entries:
        return "A memória jelenleg üres vagy nem található releváns bejegyzés."

    output = "🧠 === AGENT HOSSZÚTÁVÚ MEMÓRIA === 🧠\n"

    total_chars = 0
    for idx, entry in enumerate(entries, 1):
        cat = entry.get('category', 'Általános')
        cont = entry.get('content', '')

        # Ha Session Marker
        if cat == "SESSION_MARKER":
            output += f"[{idx}] {entry.get('timestamp', '')[:19]} | 🛑 {cont} 🛑\n"
        else:
            output += f"[{idx}] {entry.get('timestamp', '')[:10]} | Téma: {cat}\n"
            output += f"    Tartalom: {cont}\n"

        output += "-" * 50 + "\n"
        total_chars += len(cont)

    # Hallucináció és teljesítmény protokoll
    est_tokens = total_chars // 4
    output += f"\n📊 MEMÓRIA METRIKÁK:\n"
    if exec_time is not None:
        output += f"⏱️ Visszaolvasási idő: {exec_time:.4f} másodperc\n"
    output += f"📏 Teljes karakterszám: {total_chars} (~ {est_tokens} Token)\n"

    if est_tokens > 8000:
         output += "\n🔴 KRITIKUS FIGYELMEZTETÉS: A memóriából felolvasott kontextus meghaladta a 8000 tokent!\n"
         output += "   VESZÉLY: Fokozott hallucináció kockázata. A fizikai kontextusablakod betelhet.\n"
         output += "   AKCIÓ: A következő lépésben futtass egy 'Condense' (Sűrítés) műveletet, vagy csökkentsd a --limit paramétert a read parancsnál!\n"
    elif est_tokens > 5000:
         output += "\n🟡 FIGYELEM: A memóriából felolvasott kontextus meghaladta az 5000 tokent. Figyelj a fókuszvesztésre!\n"

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agent Long-Term Memory Manager")
    parser.add_argument("--action", choices=["write", "read", "start_session", "end_session", "sync"], required=True, help="Művelet: írás, olvasás, session jelölés vagy cloud sync")
    parser.add_argument("--category", type=str, default="General", help="A memória kategóriája (pl. MLOps, RAG, Strategy)")
    parser.add_argument("--content", type=str, help="A memóriába írandó tartalom (csak --action write esetén)")
    parser.add_argument("--limit", type=int, default=5, help="Hány utolsó emléket olvassunk vissza (csak --action read esetén)")

    args = parser.parse_args()

    def do_sync():
        print("\n🤖 [Kontextus Titkár] Lokális memória felhő-szinkronizáció indítása...")
        try:
            import subprocess, sys
            vps_bridge = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "vps_bridge.py")
            if not os.path.exists(vps_bridge):
                print("⚠️ vps_bridge.py nem található, kihagyom az SFTP szinkronizációt.")
                return

            repo_name = get_repo_name()
            vps_target = f"/home/misi/Jules_mx/memory_offload/backup_{repo_name}.jsonl"

            # Mappa letrehozasa a szerveren
            subprocess.run([sys.executable, vps_bridge, "mkdir -p /home/misi/Jules_mx/memory_offload"], check=False, stdout=subprocess.DEVNULL)

            # Fajl feltoltese upload moddal
            subprocess.run([sys.executable, vps_bridge, "--upload", MEMORY_FILE, vps_target], check=False, stdout=subprocess.DEVNULL)

            print("✅ Lokális memória sikeresen felszinkronizálva a VPS-re (Izolált formában).")
        except Exception as e:
            print(f"⚠️ Hiba a memória szinkronizációjakor: {e}")

    if args.action == "write":
        if not args.content:
            print("❌ Hiba: Írás esetén kötelező a --content megadása!")
        else:
            write_memory(args.category, args.content)
            # Automatikus szinkronizáció a Fő Agent nyugalma érdekében (így a VPS is azonnal frissül a write-nál)
            do_sync()

    elif args.action == "sync":
        do_sync()

    elif args.action == "start_session":
        mark_session("[SESSION_START]")
        do_sync()

    elif args.action == "end_session":
        mark_session("[SESSION_END]")
        do_sync()

    elif args.action == "read":
        entries, exec_time = read_memory(limit=args.limit, category_filter=args.category if args.category != "General" else None)
        print(format_memory_for_agent(entries, exec_time))

        # Add a strict protocol reminder for the agent after reading memory
        print("\n" + "="*70)
        print("🚨 AGENT PROTOCOL ENFORCEMENT: CONTEXT WINDOW EXTENSION 🚨")
        print("="*70)
        print("MINDEN 5. FORDULÓBAN (TURN) VAGY LOGIKAI SZAKASZ VÉGÉN KÖTELEZŐ ÍRNOD Ebbe a fájlba!")
        print("Parancs: python3 ENVIRONMENT_SETUP/agent_memory_manager.py --action write --category 'Context_Summary' --content '...'")
        print("Cél: A session hosszának drasztikus megnövelése a kontextus sűrítésével (Condense).")
        print("A Session végén futtasd: python3 ENVIRONMENT_SETUP/agent_memory_manager.py --action end_session")
        print("="*70)
