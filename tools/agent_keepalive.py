import time
import os
import sys
import datetime

def run_daemon():
    """
    Egy nagyon könnyű (0.01% CPU), végtelen ciklusú háttérfolyamat (Daemon),
    amely nemcsak az Agent UI (Cloudflare/Docker) fagyását akadályozza meg
    szívveréssel (I/O event generálás), hanem SUPERVISOR-ként is működik.

    Ha a Hosszútávú Memória fájlt (agent_memory.jsonl) túl régóta (pl. 20 perc)
    nem módosította az Agent, hangos figyelmeztetést (ALERT) ír a logba,
    amit az Agent észrevehet, mielőtt elveszítené a kontextust!
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    keepalive_file = os.path.join(script_dir, ".agent_heartbeat")

    # Próbáljuk megtalálni a memóriafájlt a Knowledge_Base mappában
    base_dir = os.path.dirname(script_dir)
    memory_file = os.path.join(base_dir, "Knowledge_Base", "agent_memory.jsonl")

    # Mivel egy agent turn kb 2-5 perc, 15-20 perc memóriaírás nélkül már aggasztó
    MEMORY_STALE_WARNING_SECONDS = 20 * 60

    print(f"💓 [Supervisor Daemon] Elindult. Folyamatos szívverés generálása: {keepalive_file}", flush=True)
    print(f"🧠 [Supervisor Daemon] Memória figyelve: {memory_file}", flush=True)

    while True:
        try:
            current_time = time.time()

            # 1. Szívverés (Docker / Cloudflare timeout ellen)
            with open(keepalive_file, "w") as f:
                f.write(str(current_time))

            # 2. Memória Frissességének Ellenőrzése (Supervisor)
            if os.path.exists(memory_file):
                last_modified = os.path.getmtime(memory_file)
                time_since_modified = current_time - last_modified

                if time_since_modified > MEMORY_STALE_WARNING_SECONDS:
                    minutes_stale = int(time_since_modified / 60)
                    print(f"
🚨 [SUPERVISOR ALERT] AZ AGENT ELFELEJTETTE ÍRNI A MEMÓRIÁT! 🚨")
                    print(f"⚠️ Utolsó írás: {minutes_stale} perce történt.")
                    print(f"👉 KÖTELEZŐ AKCIÓ: Futtasd azonnal a 'python3 ENVIRONMENT_SETUP/agent_memory_manager.py --action write ...' parancsot a szinkronizációhoz!
", flush=True)
            else:
                 print(f"⚠️ [SUPERVISOR ALERT] A memória fájl ({memory_file}) NEM LÉTEZIK! Használd a memory managert a létrehozásához!", flush=True)

            # Flusholjuk a standard kimenetet is
            sys.stdout.flush()

            # Ciklusidő: sokkal agresszívabb, hogy megakadályozzuk az IDLE fagyást (15 másodperc)
            time.sleep(15)

        except KeyboardInterrupt:
            print("
💓 [Supervisor Daemon] Leállítva.", flush=True)
            break
        except Exception as e:
            print(f"
❌ [Supervisor Daemon] Kritikus hiba a háttérben: {e}", file=sys.stderr, flush=True)
            # Az önreflexió jegyében, ha lehal a daemon, automatikusan próbáljon újraindulni kis pihenő után,
            # hogy ne maradjon a rendszer szívverés nélkül (rekurzió nélkül).
            time.sleep(10)
            print("🔄 [Supervisor Daemon] Automatikus újraindulás...", flush=True)
            continue

if __name__ == "__main__":
    run_daemon()