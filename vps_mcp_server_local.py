#!/usr/bin/env python3
"""
Jules VPS MCP Szerver (Model Context Protocol)
Ez a szerver a VPS-en (8 mag, 24GB RAM, 800GB SSD) fut, és stdio-n vagy SSE-n keresztül MCP protokollon
kiajánlja a VPS helyi erőforrásait (fájlrendszer, bash futtatás, RAG keresés, Memória Regiszter) a lokális Jules Sandboxnak.

Függőségek: mcp, anyio, sqlite3, requests
Telepítés: pip install mcp
"""
import os
import sys
import json
import sqlite3
import subprocess
import requests
import anyio
from mcp.server.fastmcp import FastMCP

# Próbáljuk betölteni a környezeti változókat a VPS ~/.env fájljából
env_file = os.path.expanduser("~/Jules_mx/.env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val


# Létrehozunk egy MCP szervert
mcp = FastMCP("Jules VPS MCP")

# --- ALAPVETŐ RENDSZER ESZKÖZÖK ---

@mcp.tool()
async def execute_bash(command: str) -> str:
    """Futtat egy bash parancsot a VPS-en és visszatér a kimenettel. Használd nagy erőforrásigényű scriptek elindításához."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.expanduser("~/Jules_mx/")
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        return f"Hibakód: {e.returncode}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"

@mcp.tool()
async def list_files_mcp(directory: str) -> str:
    """Kilistázza a VPS-en lévő fájlokat egy adott könyvtárban."""
    target_dir = os.path.expanduser(directory)
    if not os.path.exists(target_dir):
        return f"Hiba: A(z) {target_dir} könyvtár nem létezik."
    try:
        files = os.listdir(target_dir)
        return "\n".join(files)
    except Exception as e:
        return f"Hiba olvasáskor: {str(e)}"

@mcp.tool()
async def read_file_mcp(filepath: str) -> str:
    """Beolvassa egy fájl tartalmát a VPS-ről."""
    target_file = os.path.expanduser(filepath)
    if not os.path.exists(target_file):
        return f"Hiba: A fájl nem létezik: {target_file}"
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Hiba beolvasáskor: {str(e)}"


@mcp.tool()
async def git_commit_and_push(repo_path: str, commit_message: str, branch: str = "main") -> str:
    """
    VPS Git Menedzser: Hozzáadja a változásokat, commitol, és pushol egy adott branch-re a VPS-en lévő repóban.
    Kiválóan alkalmas arra, hogy a lokális homokozóból irányítva a VPS autonóm módon elmentse a kódokat a GitHubra.
    """
    target_dir = os.path.expanduser(repo_path)
    if not os.path.exists(target_dir):
        return f"Hiba: A {target_dir} mappa nem létezik."

    try:
        # Git Add
        subprocess.run(["git", "add", "."], cwd=target_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Git Commit (Ha van mit)
        commit_res = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Git Push
        push_res = subprocess.run(
            ["git", "push", "origin", branch],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return f"Git művelet sikeres.\nCommit:\n{commit_res.stdout}\nPush:\n{push_res.stderr} {push_res.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Git hiba: {e.stderr} {e.stdout}"

@mcp.tool()
async def write_file_mcp(filepath: str, content: str) -> str:
    """Fájl írása vagy felülírása a VPS-en. Használd konfigurációk vagy kódrészletek mentésére a VPS lemezére."""
    target_file = os.path.expanduser(filepath)
    try:
        os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Fájl sikeresen mentve: {target_file}"
    except Exception as e:
        return f"Hiba a fájl írásakor: {e}"


import urllib.request
from bs4 import BeautifulSoup

@mcp.tool()
async def fetch_webpage_mcp(url: str) -> str:
    """
    VPS Web Fetcher: Letölti egy megadott URL tartalmát a VPS-ről (így elrejti a lokális sandbox IP-jét).
    A HTML sallangot eltávolítja, csak a tiszta szöveget adja vissza. Használható dokumentációk olvasására.
    """
    try:
        req = urllib.request.Request(
            url,
            data=None,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7'
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read()
            soup = BeautifulSoup(html, 'html.parser')
            # Kiszedjük a felesleget
            for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
                script.decompose()
            text = soup.get_text(separator=' ', strip=True)
            # Tokenkímélés
            if len(text) > 10000:
                text = text[:10000] + "... [TRUNCATED]"
            return text
    except Exception as e:
        return f"Hiba a weboldal letöltésekor: {e}"



# --- JULES TEAM (MULTI-AGENT INBOX) ---

INBOX_DB = os.path.expanduser("~/Jules_mx/temp/jules_team_inbox.db")

def init_inbox():
    conn = sqlite3.connect(INBOX_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender TEXT,
                        target TEXT,
                        message TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_read INTEGER DEFAULT 0
                    )''')
    conn.commit()
    conn.close()

@mcp.tool()
async def send_agent_message(sender: str, target: str, message: str) -> str:
    """
    Jules Team: Üzenetet vagy feladatot küld egy másik Agentnek a VPS postaládáján keresztül.
    Példa: sender='Fő_Agent', target='EA_Jules', message='Nézd meg a MQL5_Theory mappát!'
    """
    init_inbox()
    try:
        conn = sqlite3.connect(INBOX_DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender, target, message) VALUES (?, ?, ?)", (sender, target, message))
        conn.commit()
        conn.close()
        return f"✅ Üzenet sikeresen elküldve a következőnek: {target}"
    except Exception as e:
        return f"Hiba az üzenet küldésekor: {e}"

@mcp.tool()
async def check_agent_messages(agent_name: str) -> str:
    """
    Jules Team: Lekérdezi az adott Agentnek (pl. 'EA_Jules' vagy 'Fő_Agent') címzett OLVASATLAN üzeneteket a VPS-ről.
    Lekérdezés után automatikusan olvasottá nyilvánítja őket.
    """
    init_inbox()
    try:
        conn = sqlite3.connect(INBOX_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT id, sender, timestamp, message FROM messages WHERE target = ? AND is_read = 0", (agent_name,))
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return f"📭 Nincs új olvasatlan üzenet a következőnek: {agent_name}"

        output = f"📬 {len(rows)} új üzenet érkezett a következőnek: {agent_name}\n\n"
        ids_to_mark = []
        for r in rows:
            output += f"[{r[2]}] Feladó: {r[1]}\nÜzenet: {r[3]}\n" + "-"*30 + "\n"
            ids_to_mark.append(str(r[0]))

        # Olvasottra állítás
        cursor.execute(f"UPDATE messages SET is_read = 1 WHERE id IN ({','.join(ids_to_mark)})")
        conn.commit()
        conn.close()
        return output
    except Exception as e:
        return f"Hiba az üzenetek lekérdezésekor: {e}"


# --- JULES SWARM (ELOSZTOTT FELADATKIOSZTÁS) ---

SWARM_DB = os.path.expanduser("~/Jules_mx/temp/jules_swarm_jobs.db")

def init_swarm_db():
    conn = sqlite3.connect(SWARM_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_type TEXT,
                        target_repo TEXT,
                        instruction TEXT,
                        status TEXT DEFAULT 'PENDING',
                        assigned_to TEXT,
                        result TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.commit()
    conn.close()

@mcp.tool()
async def create_swarm_job(job_type: str, target_repo: str, instruction: str) -> str:
    """
    Létrehoz egy elosztott feladatot a Jules Team számára a felhőben.
    Bármely szabad Agent felveheti és végrehajthatja a saját homokozójában.
    """
    init_swarm_db()
    try:
        conn = sqlite3.connect(SWARM_DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jobs (job_type, target_repo, instruction) VALUES (?, ?, ?)", (job_type, target_repo, instruction))
        conn.commit()
        conn.close()
        return f"✅ Feladat sikeresen létrehozva a Swarm hálózatban a {target_repo} repóhoz."
    except Exception as e:
        return f"Hiba a feladat létrehozásakor: {e}"

@mcp.tool()
async def get_next_swarm_job(agent_id: str) -> str:
    """
    Lekérdezi és lefoglalja a következő szabad (PENDING) feladatot a Swarm hálózatból.
    Az agent_id lehet a repo neve vagy a session azonosítója (pl. 'Jules_EA_Fejlesztes').
    """
    init_swarm_db()
    try:
        conn = sqlite3.connect(SWARM_DB)
        cursor = conn.cursor()
        # Keresünk egy PENDING feladatot
        cursor.execute("SELECT id, job_type, target_repo, instruction FROM jobs WHERE status = 'PENDING' ORDER BY timestamp ASC LIMIT 1")
        row = cursor.fetchone()

        if not row:
            conn.close()
            return "📭 Nincs jelenleg kiosztható feladat a Swarm hálózatban."

        job_id = row[0]
        # Lefoglaljuk a feladatot
        cursor.execute("UPDATE jobs SET status = 'IN_PROGRESS', assigned_to = ? WHERE id = ?", (agent_id, job_id))
        conn.commit()
        conn.close()

        return json.dumps({
            "job_id": job_id,
            "job_type": row[1],
            "target_repo": row[2],
            "instruction": row[3]
        }, ensure_ascii=False)
    except Exception as e:
        return f"Hiba a feladat lekérdezésekor: {e}"

@mcp.tool()
async def complete_swarm_job(job_id: int, result: str) -> str:
    """
    Jelenti a felhőnek, hogy egy feladat sikeresen befejeződött, és elmenti az eredményt.
    """
    init_swarm_db()
    try:
        conn = sqlite3.connect(SWARM_DB)
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status = 'COMPLETED', result = ? WHERE id = ?", (result, job_id))
        conn.commit()
        conn.close()
        return f"✅ A {job_id} azonosítójú feladat sikeresen lezárva a Swarmban."
    except Exception as e:
        return f"Hiba a feladat lezárásakor: {e}"

# --- GITHUB SCOUT (MINI-ÁGENS) ---



@mcp.tool()
async def github_list_user_repos(username: str) -> str:
    """
    Kilistázza egy adott GitHub felhasználó (pl. 'mihaly67') publikus repóit.
    Ha a VPS ~/.env fájljában van GITHUB_TOKEN, akkor a privátokat is látja.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        # User repói
        url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"GitHub API Hiba: {response.status_code} - {response.text}"

        repos = response.json()
        if not repos:
            return f"Nincs repo a '{username}' felhasználóhoz."

        result = f"📂 {username} GitHub Repói ({len(repos)} db):\n"
        for r in repos:
            priv = "🔒 Privát" if r.get("private") else "🌍 Publikus"
            result += f"- {r['name']} ({priv}) | 🌟 {r.get('stargazers_count', 0)} | 🔄 {r.get('updated_at')}\n"

        return result
    except Exception as e:
        return f"Hiba a GitHub lekérdezéskor: {e}"

@mcp.tool()
async def github_search_repos(query: str, limit: int = 5) -> str:
    """Keres a teljes nyílt GitHub-on repókat egy kulcsszó vagy kifejezés (pl. 'MCP server python') alapján."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={limit}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"GitHub API Hiba: {response.status_code} - {response.text}"

        data = response.json()
        items = data.get("items", [])
        if not items:
            return f"Nincs találat a '{query}' keresésre."

        result = f"🔍 Top {len(items)} GitHub találat a '{query}' szóra:\n\n"
        for r in items:
            result += f"📦 Repo: {r['full_name']}\n"
            result += f"🌟 Csillagok: {r.get('stargazers_count', 0)}\n"
            result += f"📝 Leírás: {r.get('description', 'Nincs leírás')}\n"
            result += f"🔗 URL: {r.get('html_url')}\n"
            result += "-" * 40 + "\n"

        return result
    except Exception as e:
        return f"Hiba a GitHub lekérdezéskor: {e}"

@mcp.tool()
async def github_read_file(owner: str, repo: str, file_path: str, branch: str = "main") -> str:
    """
    Letölti és beolvassa egy konkrét fájl tartalmát a GitHub-ról anélkül, hogy le kellene klónozni a repót!
    Példa: owner='mihaly67', repo='MX_LINUX-LINUX_OPTIMALISATION', file_path='README.md'
    """
    headers = {"Accept": "application/vnd.github.v3.raw"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 404:
            return f"Hiba: A fájl nem található: {file_path} a {branch} branchen."
        elif response.status_code != 200:
            return f"GitHub API Hiba: {response.status_code} - {response.text}"

        content = response.text
        if len(content) > 15000:
            return content[:15000] + "\n\n... [TRUNCATED - A fájl túl hosszú a teljes megjelenítéshez]"

        return content
    except Exception as e:
        return f"Hiba a fájl letöltésekor: {e}"

# --- RAG ÉS MEMÓRIA (ARCHIVAL & RECALL) ESZKÖZÖK ---




RAG_DATABASES = {
    "Chatbot": os.path.expanduser("~/Rag_epites, chatbot_csv_data_llm_RAG/RAG_CHATBOT_CSV_DATA_LLM_github.db"),
    "MQL5_Theory": os.path.expanduser("~/MQL5_Theory/mql5_native_knowledge.db"),
    "BRAIN2": os.path.expanduser("/home/misi/BRAIN2_DEV_RAG/brain2_dev_knowledge.db"),
    "Gerilla": os.path.expanduser("~/Gerilla_RAG/Gerilla_RAG.db"),
    "MX_Linux": os.path.expanduser("~/MX_LINUX_RAG/mx_linux_knowledge.db")
}

@mcp.tool()
async def search_rag_database(rag_name: str, keyword: str, limit: int = 3) -> str:
    """
    RAG Archival Memory kereső.
    A megadott tudásbázisban (Chatbot, BRAIN2, Gerilla, MX_Linux) keres SQL LIKE vagy egzakt illeszkedés alapján.
    A lokális agent ezt használja tudás kinyerésére a VPS gigantikus lemezéről!
    """
    if rag_name not in RAG_DATABASES:
        return f"Hiba: Ismeretlen RAG adatbázis. Elérhetőek: {', '.join(RAG_DATABASES.keys())}"

    db_path = RAG_DATABASES[rag_name]
    if not os.path.exists(db_path):
        return f"Hiba: A(z) {db_path} adatbázis fájl nem található a VPS-en."

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Gyors SQL text search a RAG tartalmában
        query = f"%{keyword}%"
        cursor.execute("SELECT filepath, content FROM rag_data WHERE content LIKE ? LIMIT ?", (query, limit))
        results = cursor.fetchall()
        conn.close()

        if not results:
            return f"Nincs találat a '{keyword}' kulcsszóra a {rag_name} RAG-ban."

        output = f"🔍 {len(results)} találat a {rag_name} RAG-ban a '{keyword}' szóra:\n\n"
        for filepath, content in results:
            # Csak az elejét mutatjuk, hogy ne robbanjon fel az MCP csatorna
            snippet = content[:1500] + ("..." if len(content) > 1500 else "")
            output += f"📄 Fájl: {filepath}\n{snippet}\n"
            output += "-" * 50 + "\n"

        return output
    except Exception as e:
        return f"Adatbázis lekérdezési hiba: {e}"

# --- HIERARCHIKUS MEMÓRIA REGISZTER (CORE MEMORY / CONTEXT) ---

MEMORY_REGISTER_FILE = os.path.expanduser("~/Jules_mx/temp/mcp_memory_register.json")

def init_memory_register():
    if not os.path.exists(MEMORY_REGISTER_FILE):
        with open(MEMORY_REGISTER_FILE, "w", encoding="utf-8") as f:
            json.dump({"Core": {}, "Archival_Pointers": []}, f)

@mcp.tool()
async def read_memory_register() -> str:
    """
    Kiolvassa a VPS-en lévő globális Memória Regisztert.
    Ezt használhatja a lokális Agent a kontextus gyors helyreállítására (Core Memory).
    """
    init_memory_register()
    with open(MEMORY_REGISTER_FILE, "r", encoding="utf-8") as f:
        return f.read()

@mcp.tool()
async def write_memory_register(key: str, value: str) -> str:
    """
    Ír a VPS globális Memória Regiszterébe.
    Hasznos hosszú távú állapotok, feladat-listák (Task Queue) és kontextus mentésére.
    """
    init_memory_register()
    try:
        with open(MEMORY_REGISTER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["Core"][key] = value

        with open(MEMORY_REGISTER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return f"✅ '{key}' sikeresen elmentve a VPS Memória Regiszterbe."
    except Exception as e:
        return f"Hiba a memória mentésekor: {e}"


@mcp.tool()
async def create_full_backup() -> str:
    """Elindítja a VPS-en a teljes biztonsági mentést (Jules_mx + RAG adatbázisok). A folyamat hosszú lehet."""
    try:
        script_path = os.path.expanduser("~/Jules_mx/scripts/vps_backup_script.sh")
        if not os.path.exists(script_path):
            return "Hiba: A backup script nem található a VPS-en."

        result = subprocess.run(
            ["bash", script_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return f"Mentés sikeres:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Hiba a mentés során: {e.stderr}"

def main():
    """Futtatja a szervert stdio módban."""
    print("🚀 Jules VPS MCP Szerver elindítva (stdio módban).", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    main()
