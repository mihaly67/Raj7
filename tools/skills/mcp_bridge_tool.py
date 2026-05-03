import subprocess
import sys
import json
import shlex

def run_mcp_tool(tool_name, tool_args):
    try:
        from vps_bridge import run_on_vps
    except ImportError:
        import os
        sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        try:
             from vps_bridge import run_on_vps
        except:
             return "Hiba: vps_bridge nem talalhato a Python path-ban."
             
    # A JSON payload escape-elése bash híváshoz, hogy a bonyolult stringek ne hasaljanak el.
    args_json = json.dumps(tool_args)
    safe_args = shlex.quote(args_json)
    
    # Invoke the mcp cli on the VPS
    cmd = f"mcp call {tool_name} --args {safe_args}"
    success, output = run_on_vps(cmd)
    
    return output

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Hasznalat: python3 mcp_bridge_tool.py <tool_neve> [arg1] [arg2] ...")
        sys.exit(1)
        
    tool = sys.argv[1]
    
    # Primitiv parser, ami elfogadja pozíció alapján az argumentumokat, amit a rajtagok gyakran rontanak el kwargs-re
    args_dict = {}
    
    if tool == 'execute_bash' and len(sys.argv) > 2:
         args_dict['command'] = sys.argv[2]
    elif tool == 'execute_python' and len(sys.argv) > 2:
         args_dict['code'] = sys.argv[2]
    elif tool == 'get_next_swarm_job' and len(sys.argv) > 2:
         args_dict['agent_id'] = sys.argv[2]
    elif tool == 'complete_swarm_job' and len(sys.argv) > 3:
         args_dict['job_id'] = int(sys.argv[2])
         args_dict['result'] = sys.argv[3]
    elif tool == 'search_rag_database' and len(sys.argv) > 3:
         args_dict['rag_name'] = sys.argv[2]
         args_dict['keyword'] = sys.argv[3]
         
    res = run_mcp_tool(tool, args_dict)
    print(res)
