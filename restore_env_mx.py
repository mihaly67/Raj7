import os
import sys
import shutil
import zipfile
import subprocess
import sqlite3

def install_dependencies():
    print("🔧 Függőségek ellenőrzése és telepítése...")
    required = ["gdown", "faiss-cpu", "sentence-transformers", "numpy", "pandas", "colorama", "paramiko", "mcp", "beautifulsoup4"]
    for pkg in required:
        try:
            module_name = pkg
            if pkg == "sentence-transformers": module_name = "sentence_transformers"
            elif pkg == "faiss-cpu": module_name = "faiss"
            __import__(module_name.replace("-", "_"))
        except ImportError:
            print(f"   ⚠️ '{pkg}' hiányzik. Telepítés...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg], stdout=subprocess.DEVNULL)
                print(f"   ✅ '{pkg}' telepítve.")
            except Exception as e:
                print(f"   ❌ Hiba a(z) '{pkg}' telepítésekor: {e}")

install_dependencies()

try:

    from colorama import Fore, Style, init
    init(autoreset=True)
except ImportError:
    class Fore: GREEN=""; RED=""; YELLOW=""; CYAN=""; RESET=""
    class Style: BRIGHT=""

ENVIRONMENT_RESOURCES = {
    "RAG_CHATBOT_CSV_DATA_LLM_SKILL_RAG": {
        "id": "1hNl4JYrms427u94H48kpkb39OJ5C5AhN",
        "file": "RAG_CHATBOT_CSV_DATA_LLM_SKILL_RAG.zip",
        "extract_to": "Knowledge_Base/RAG_DB",
        "check_file": "RAG_CHATBOT_CSV_DATA_LLM_github.db",
        "type": "zip",
        "preserve_dir": False
    },
    "MX_LINUX_KNOWLEDGE_RAG": {
        "id": "15Peu8cVlKK5cJYOlZMElOc9ybd5e2gIx",
        "file": "mx_linux_rag.zip",
        "extract_to": "Knowledge_Base/RAG_DB",
        "check_file": "mx_linux_knowledge.db",
        "type": "zip",
        "preserve_dir": False
    },
    "GERILLA_RAG": {
        "id": "1re0EoQ1H-QauiCmRfvozJlFISL6FSQI3",
        "file": "GERILLA_RAG.zip",
        "extract_to": "Knowledge_Base/RAG_DB",
        "check_file": "Gerilla_RAG.db",
        "type": "zip",
        "preserve_dir": False
    }
}

def log(msg, color=Fore.GREEN): print(f"{color}{msg}{Style.RESET_ALL}")

def hoist_files(target_dir, check_file):
    if not check_file: return False
    found_path = None
    for root, dirs, files in os.walk(target_dir):
        if check_file in files:
            found_path = os.path.join(root, check_file)
            break
    if not found_path: return False
    source_dir = os.path.dirname(found_path)
    if os.path.abspath(source_dir) == os.path.abspath(target_dir): return True
    log(f"   ⬆️ Fájlok felmozgatása innen: {source_dir}", Fore.CYAN)
    for item in os.listdir(source_dir):
        try: shutil.move(os.path.join(source_dir, item), os.path.join(target_dir, item))
        except: pass
    try:
        if not os.listdir(source_dir): os.rmdir(source_dir)
    except: pass
    return True

def check_sqlite_integrity(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return bool(tables)
    except sqlite3.Error: return False

def process_resource(key, config):
    print(f"\n🔧 Feldolgozás: {key}...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_dir = os.path.join(script_dir, config.get("extract_to"))
    check_file = config.get("check_file")
    zip_name = os.path.join(script_dir, config["file"])
    drive_id = config["id"]
    preserve_dir = config.get("preserve_dir", False)
    check_path = os.path.join(target_dir, check_file) if check_file and target_dir else None

    is_valid = False
    if check_path and os.path.exists(check_path):
        if check_path.endswith(".db") or check_path.endswith(".sqlite"):
            is_valid = check_sqlite_integrity(check_path)
        else:
            is_valid = os.path.getsize(check_path) > 1024

    if is_valid:
        log(f"   ✅ {key} rendben (Ellenőrizve).")
        return

    if check_path and os.path.exists(check_path) and not preserve_dir:
        log(f"   ⚠️ {key} sérült vagy érvénytelen. Törlés és újraletöltés...", Fore.YELLOW)
        try:
            if os.path.isdir(target_dir): shutil.rmtree(target_dir)
        except: pass
    elif not os.path.exists(target_dir):
        log(f"   ⚠️ {key} célkönyvtára ({target_dir}) nem létezik. Létrehozás...", Fore.YELLOW)

    if not os.path.exists(zip_name):
        log(f"   📥 Letöltés: {config['file']} (ID: {drive_id})...", Fore.CYAN)
        try: gdown.download(id=drive_id, output=zip_name, quiet=False)
        except Exception as e:
            log(f"   ❌ Letöltési hiba: {e}", Fore.RED)
            return

    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
        log(f"   📦 Kicsomagolás ide: {target_dir}...", Fore.CYAN)
        try:
            with zipfile.ZipFile(zip_name, 'r') as z: z.extractall(target_dir)
            if check_file:
                hoist_files(target_dir, check_file)
                final_check_path = os.path.join(target_dir, check_file)
                if not os.path.exists(final_check_path): log(f"   ❌ Hiba: {check_file} nem található kicsomagolás után sem!", Fore.RED)
                else: log(f"   ✨ {key} Sikeresen telepítve.", Fore.GREEN)
        except zipfile.BadZipFile:
            log("   ❌ Sérült Zip Fájl! Törlés...", Fore.RED)
            os.remove(zip_name)
        except Exception as e: log(f"   ❌ Kicsomagolási hiba: {e}", Fore.RED)
        finally:
            if os.path.exists(zip_name): os.remove(zip_name)

def main():
    print(f"{Fore.CYAN}=== 🚀 MX LINUX OPTIMIZATION RAG DEPLOYMENT ==={Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}🔌 RAG Vékonykliens mód aktív. (Az adatbázisokat nem töltjük le lokálisan, a VPS szolgálja ki őket!){Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}💓 Indítom az Agent Keep-Alive Démont a háttérben...{Style.RESET_ALL}")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(script_dir, "supervisor.log")
    keepalive_path = os.path.join(script_dir, "tools", "agent_keepalive.py")
    
    if os.path.exists(keepalive_path):
        log_file = open(log_file_path, "w")
        subprocess.Popen([sys.executable, keepalive_path], stdout=log_file, stderr=log_file)
    else:
        print(f"{Fore.YELLOW}⚠️ agent_keepalive.py nem található a tools mappában!{Style.RESET_ALL}")

    print(f"{Fore.CYAN}🧠 Memória [SESSION_START] inicializálása a háttérben...{Style.RESET_ALL}")
    memory_manager_path = os.path.join(script_dir, "ENVIRONMENT_SETUP", "agent_memory_manager.py")
    if os.path.exists(memory_manager_path):
        # Csak szinkronizáljuk a memóriát, de nem írjuk be a felesleges SESSION_START markert minden futtatáskor,
        # mert az teliszemeteli a memóriát.
        subprocess.run([sys.executable, memory_manager_path, "--action", "sync"])
        print(f"{Fore.CYAN}🧠 A VPS Titkár aszinkron felébresztése befejeződött.{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠️ agent_memory_manager.py nem található!{Style.RESET_ALL}")
        

    print(f"\n{Fore.CYAN}🔑 Nyílt SSH kulcs (Gerilla protokoll) inicializálása és VPS hitelesítés...{Style.RESET_ALL}")
    secrets_dir = os.path.join(script_dir, "tools", "secrets")
    os.makedirs(secrets_dir, exist_ok=True)

    key_path = os.path.join(secrets_dir, "jules_vps_key")

    if not os.path.exists(key_path):
        # A környezeti változóból próbáljuk beolvasni a privát kulcsot
        vps_ssh_key = os.environ.get("VPS_SSH_KEY")
        if vps_ssh_key:
            print(f"   ⚙️ SSH kulcs importálása a környezeti változóból...")
            with open(key_path, "w") as f:
                f.write(vps_ssh_key.replace("\\n", "\n"))
            os.chmod(key_path, 0o600)
            print(f"{Fore.GREEN}   ✅ SSH kulcs importálva és beállítva.{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}   ⚠️ SSH kulcs hiányzik. Kérjük állítsd be a VPS_SSH_KEY környezeti változót!{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}   ✅ SSH kulcsok már léteznek.{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}🚀 Gemini API integráció beállítása a VPS-en...{Style.RESET_ALL}")
    gemini_key = os.environ.get("VPS_GEMINI_API_KEY")
    if gemini_key:
        try:
            from tools.vps_bridge import run_on_vps, upload_to_vps
            # Hozzáadjuk a .env fájlhoz a VPS-en biztonságosan (append, hogy ne írjuk felül a régit)
            cmd = f"echo 'GEMINI_API_KEY={gemini_key}' >> ~/Jules_mx/.env && chmod 600 ~/Jules_mx/.env"
            success, result = run_on_vps(cmd)
            if success:
                print(f"{Fore.GREEN}   ✅ Gemini API kulcs szinkronizálva a VPS-re.{Style.RESET_ALL}")

                # Biztosítjuk, hogy a Gemini Scout script is felkerül a szerverre!
                gemini_script_local = os.path.join(script_dir, "tools", "skills", "gemini_scout.py")
                if os.path.exists(gemini_script_local):
                    print(f"   📤 Gemini Scout script feltöltése...")
                    success, msg = upload_to_vps(gemini_script_local, "/home/misi/Jules_mx/scripts/gemini_scout.py")
                    if success:
                        print(f"{Fore.GREEN}   ✅ Gemini Scout sikeresen telepítve a VPS-re.{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}   ❌ Gemini Scout feltöltés sikertelen: {msg}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}   ❌ Hiba a Gemini kulcs VPS-re másolásakor: {result}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}   ❌ Hiba a VPS_GEMINI_API_KEY beállításánál: {e}{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}   ⚠️ Nincs VPS_GEMINI_API_KEY megadva a környezeti változókban. A VPS-en lévő kulcs nem frissül.{Style.RESET_ALL}")

    print(f"\n{Fore.GREEN}✅ KÖRNYEZET KÉSZ. RAG RENDSZER AKTÍV.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
