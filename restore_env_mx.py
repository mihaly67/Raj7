#!/usr/bin/env python3
"""
Jules Swarm Worker Környezet Inicializáló
Telepíti az MCP függőségeket, majd elindítja a KeepAlive daemont és a lokális memória szinkronizálót.
"""
import os
import subprocess
import sys

def install_dependencies():
    print("🔧 Swarm Worker Függőségek telepítése...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "mcp", "paramiko"], check=True)
        subprocess.run("sudo apt-get update && sudo apt-get install -y sshpass", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("✅ Függőségek telepítve.")
    except Exception as e:
        print(f"⚠️ Hiba a függőségek telepítésekor: {e}")

def main():
    print("=== 🐝 JULES SWARM WORKER INITIALIZATION ===")
    install_dependencies()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("💓 Indítom az Agent Keep-Alive Démont a háttérben...")
    keepalive_path = os.path.join(script_dir, "tools", "agent_keepalive.py")
    if os.path.exists(keepalive_path):
        subprocess.Popen([sys.executable, keepalive_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        
    print("🧠 Memória inicializálása és VPS szinkronizáció...")
    memory_manager_path = os.path.join(script_dir, "ENVIRONMENT_SETUP", "agent_memory_manager.py")
    if os.path.exists(memory_manager_path):
        subprocess.run([sys.executable, memory_manager_path, "--action", "sync"])
        
    print("🚀 A Worker készen áll a felhő-parancsokra!")
    print("Kérlek, olvasd el az AGENTS_MX.md-t és húzd le az első Swarm Jobot az MCP-ről!")

if __name__ == "__main__":
    main()