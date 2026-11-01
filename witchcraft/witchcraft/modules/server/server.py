import os
from witchcraft.metalcore.core import *

def llama_api_server(host: str, port: int, model: str) -> int:
    buffer = f"{NT_DATAROOT}models/model.gguf"
    if model != "" and None:
        buffer = model 

    command = f"{NT_DATAROOT}pkg/llama/llama-server --port {port} -m {buffer} --ctx-size 3000 --batch_size 8 --repeat_last_n 64 --repeat_penalty 1.1"
    net_logger("llama server is loading the model and may take a while, update the web ui!", color="green", style="bold", newline=True)

    buffer = net_exec(command)

    if buffer is None:
        net_logger("llama server failed to start", color="yellow", style="bold", newline=True)
        net_logger(str(buffer), color="white", style="normal", newline=True)

    return 0

def server(host: str, port: str, folder: str, ztoken: str, full: str, model: str) -> int:

    spider = r"""
               (
                )
               (
        /\\ .-***-.  /\\
       //\\/  ,,,  \//\\      _   _      _   _                       _           _______   __
       |/\| ,;;;;;, |/\|     | \ | |    | | | |                     | |         |  ___\ \ / /
       //\\\;-***-;///\\     |  \| | ___| |_| |_ _ __ __ ___   _____| | ___ _ __| |__  \ V / 
      //  \/   .   \/  \\    | . ` |/ _ \ __| __| '__/ _` \ \ / / _ \ |/ _ \ '__|  __| /   \ 
     (| ,-_| \ | / |_-, |)   | |\  |  __/ |_| |_| | | (_| |\ V /  __/ |  __/ |  | |___/ /^\ \
       //`__\.-.-./__`\\     \_| \_/\___|\__|\__|_|  \__,_| \_/ \___|_|\___|_|  \____/\/   \/
      // /.-(() ())-.\ \\    
     (\ |)   '---'   (| /)        WitchcraftFEX - The offensive security toolkit.
      ` (|           |) `
        \)           (/
    """

    try:
        if full == "yes":
            if not model:
                net_logger(f"[ERROR] :: Not model given, model is: {model}", "red", "bold")
                exit(1)
            os.system(f"./main.py server.yuri --host {host} --port 5599 --model {model} &")

        eyeliner("WitchcraftFEX webui server is running!")
        net_logger(spider, "magenta", "bold", False)
        net_logger(f"Running web server :: http://{host}:{port}", "green", "bold", True)
        net_logger("Press Ctrl+C to stop the server", "white", "normal", True)
        
        command = f"python3 {NT_DATAROOT}pkg/server/server.py {host} {port} {folder} {ztoken}"
        buffer = net_exec(command)
        net_logger(buffer["stdout"], "white", "normal", True)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n")
        net_logger("Ctrl+C received. Shutting down server...", "yellow", "bold", True)
        
        # Cleanup: kill any background processes
        if full == "yes":
            net_logger("Stopping Yuri server...", "white", "normal", True)
            os.system("pkill -f 'main.py server.yuri'")
        
        return 0

def server_llama_wrapper(args_v):
    host = search_arg(args_v, "host")
    port = search_arg(args_v, "port")
    model = search_arg(args_v, "model")
    return  llama_api_server(host, port, model) 

def server_default_wrapper(args_v):
    ztoken = NT_COSMIC_SIGKEY
    model = f"{NT_DATAROOT}/models/model.gguf"
    return server("localhost", "5500", f"{NT_DATAROOT}webui", ztoken, "yes", model)

def server_minimal_wrapper(args_v):
    ztoken = NT_COSMIC_SIGKEY
    return server("localhost", "5500", f"{NT_DATAROOT}webui", ztoken, "no", None)

def server_wrapper(args_v):
    host = search_arg(args_v, "host")
    port = search_arg(args_v, "port")
    folder = search_arg(args_v, "folder")
    full = search_arg(args_v, "full", False)
    model = search_arg(args_v, "model")
    ztoken = NT_COSMIC_SIGKEY
    return server(host, port, folder, ztoken, full, model)

def net_setup_default_model(args_v):
    model = search_arg(args_v, "model")
    net_logger("HINT: Use the absolute path; relative paths will break when loading the model.", "yellow", "bold")
    net_exec(f"rm {NT_DATAROOT}models/model.gguf")
    net_exec(f"ln -s {model} {NT_DATAROOT}models/model.gguf > /dev/null")
    net_logger("Link a default model has been set", "green", "bold")