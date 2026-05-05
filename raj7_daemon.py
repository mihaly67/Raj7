import os
import sys
import time
import sqlite3
import subprocess
import requests
import json

# ==========================================
# JULES SWARM AGENT DAEMON (VPS NATIVE)
# ==========================================

AGENT_ID = 'raj1'
SWARM_DB = os.path.expanduser('~/Jules_mx/temp/jules_swarm_jobs.db')
WORKSPACE = f'/home/misi/Swarm_Agents/{AGENT_ID}'

# Az agy ezentul a lokalis Ollama kiszolgalo a VPS-en. Nincs tobb felho API.
OLLAMA_URL = 'http://localhost:11434/api/generate'
# A kódoláshoz a legokosabb (de CPU-n lassabb) modellt használjuk
OLLAMA_MODEL = 'qwen2.5:1.5b' 

def get_next_job():
    conn = sqlite3.connect(SWARM_DB)
    cursor = conn.cursor()
    
    # 1. Van-e Szigoruan Nekem szolo PENDING feladat?
    cursor.execute("SELECT id, job_type, instruction FROM jobs WHERE status = 'PENDING' AND target_repo = ? ORDER BY timestamp ASC LIMIT 1", (AGENT_ID,))
    row = cursor.fetchone()
    
    # 2. Ha nincs, van-e SWARM_POOL-os (Szabad rablaskent)?
    if not row:
         cursor.execute("SELECT id, job_type, instruction FROM jobs WHERE status = 'PENDING' AND target_repo = 'SWARM_POOL' ORDER BY timestamp ASC LIMIT 1")
         row = cursor.fetchone()
         
    if row:
        job_id = row[0]
        cursor.execute("UPDATE jobs SET status = 'IN_PROGRESS', assigned_to = ? WHERE id = ?", (AGENT_ID, job_id))
        conn.commit()
        conn.close()
        return {'id': row[0], 'type': row[1], 'instruction': row[2]}
        
    conn.close()
    return None

def complete_job(job_id, result_msg):
    conn = sqlite3.connect(SWARM_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = 'COMPLETED', result = ? WHERE id = ?", (result_msg, job_id))
    conn.commit()
    conn.close()

def ask_ollama(prompt):
    print(f"   [Ollama] Kérés indítása a {OLLAMA_MODEL} modellhez... (Ez CPU-n percekig is tarthat!)", flush=True)
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    
    try:
        # A CPU inference lassu, foleg 8B modellnel, igy 10 perces (600s) timeout kell
        resp = requests.post(OLLAMA_URL, json=payload, timeout=1800)
        if resp.status_code == 200:
            return resp.json().get('response', 'Ures valasz az Ollamatol.')
        else:
            return f"Ollama API Hiba: {resp.status_code} - {resp.text}"
    except requests.exceptions.Timeout:
         return "Ollama Hiba: Timeout (Túl sokáig gondolkodott a CPU)."
    except Exception as e:
        return f"Ollama Kivetel: {e}"

def execute_bash(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=WORKSPACE)
        return result.stdout if result.stdout else "Sikeres vegrehajtas (nincs kimenet)"
    except subprocess.CalledProcessError as e:
        return f"Hiba: {e.stderr} {e.stdout}"

def main_loop():
    print(f"🚀 Swarm Daemon indul: {AGENT_ID}", flush=True)
    os.makedirs(WORKSPACE, exist_ok=True)
    
    while True:
        try:
            job = get_next_job()
            if job:
                print(f"\n📥 Uj feladat: {job['id']} - {job['type']}", flush=True)
                
                # Ha ez egy sima bash script (pl. RAG darabolás)
                if 'python3' in job['instruction'] and '.py' in job['instruction']:
                    print("-> Bash script feladat futtatasa...", flush=True)
                    output = execute_bash(job['instruction'])
                    complete_job(job['id'], f"Bash kimenet: {output}")
                
                # Ha szoveges kerdes/kodolas (LLM igenyeltetik)
                else:
                    print("-> Lokális Ollama (Agy) meghivasa a feladathoz...", flush=True)
                    ai_response = ask_ollama(job['instruction'])
                    complete_job(job['id'], f"AI Valasz: {ai_response}")
                    print(f"✅ Feladat befejezve!", flush=True)
                    
            else:
                time.sleep(5)
                
        except Exception as e:
            print(f"❌ Kritikus hiba a ciklusban: {e}", flush=True)
            time.sleep(5)

if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True)
    main_loop()
