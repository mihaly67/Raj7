import paramiko
import os
import sys

VPS_IP = "5.189.163.88"
VPS_USER = "misi"

def get_auth_kwargs(password=None):
    kwargs = {}

    # 0. Jelszó paraméterből (legmagasabb prioritás visszamenőleges kompatibilitás miatt)
    if password:
        kwargs["password"] = password
        return kwargs

    # 1. Jelszó környezeti változóból
    pwd = os.environ.get("VPS_PWD")
    if pwd:
        kwargs["password"] = pwd
        return kwargs

    # 2. SSH kulcs fájlból (ha létezik)
    key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets", "jules_vps_key")
    if os.path.exists(key_file):
        kwargs["key_filename"] = key_file
        return kwargs

    # 3. SSH kulcs környezeti változóból (ha Dockerben fut, nem file-ban adják át)
    key_env = os.environ.get("VPS_SSH_KEY")
    if key_env:
        import io
        key_obj = paramiko.Ed25519Key.from_private_key(io.StringIO(key_env))
        kwargs["pkey"] = key_obj
        return kwargs

    return kwargs

def run_on_vps(command, password=None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    auth_kwargs = get_auth_kwargs(password)

    if not auth_kwargs:
        return False, "❌ Hiba: Nincs érvényes hitelesítési mód (kulcs fájl, VPS_SSH_KEY env, vagy VPS_PWD env)."

    try:
        client.connect(hostname=VPS_IP, port=22, username=VPS_USER, timeout=10, **auth_kwargs)

        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode("utf-8")
        error = stderr.read().decode("utf-8")

        client.close()
        return True, output if output else error

    except Exception as e:
        return False, str(e)

def upload_to_vps(local_path, remote_path, password=None):
    """SFTP feltöltés a VPS Második Agyára (tehermentesítés)."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    auth_kwargs = get_auth_kwargs(password)

    if not auth_kwargs:
        return False, "❌ Hiba: Nincs érvényes hitelesítési mód."

    try:
        client.connect(hostname=VPS_IP, port=22, username=VPS_USER, timeout=10, **auth_kwargs)
        sftp = client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()
        client.close()
        return True, f"✅ Sikeres feltöltés: {local_path} -> {remote_path}"
    except Exception as e:
        return False, f"❌ Hiba a feltöltésnél: {e}"

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--upload":
        success, out = upload_to_vps(sys.argv[2], sys.argv[3])
        print(out)
    elif len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        success, out = run_on_vps(cmd)
        print(out)
    else:
        print("💡 Használat: \n Parancs futtatása: python3 tools/vps_bridge.py <parancs>\n Fájl feltöltése: python3 tools/vps_bridge.py --upload <helyi_fájl> <távoli_fájl>")
