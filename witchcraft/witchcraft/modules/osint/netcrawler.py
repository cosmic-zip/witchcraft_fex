from witchcraft.metalcore.core import *
from ipaddress import ip_network, IPv4Address
from datetime import datetime

NON_PUBLIC = [
    "0.0.0.0/8",
    "10.0.0.0/8",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "100.64.0.0/10",
    "224.0.0.0/4",
    "198.18.0.0/15",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "240.0.0.0/4",
]

defstr = "sudo nmap -sS -sV -A -oX - --min-parallelis 16 --reason --script=default,safe,vuln"
non_public_networks = [ip_network(n) for n in NON_PUBLIC]
def is_public(ip):
    for net in non_public_networks:
        if ip in net:
            return False
    return True

def search_ci_badguys(ip_obj):
    cibadguys = os.path.join(NT_DATAROOT, "osint/ip/ci-badguys.txt")
    with open(cibadguys, "r") as file:
        for line in file:
            if line.rstrip("\n") == ip_obj:
                return f"\n<cibadguys>found</cibadguys>"
    return f"\n<cibadguys>not_found</cibadguys>"

def netcrawler_for_all_ipv4(args):
    eyeliner("[netcrawler] Run a scanner in hole internet! Good luck xD")
    for ip_int in range(1 << 24, 2**32):
        oct1 = (ip_int >> 24) & 255
        oct2 = (ip_int >> 16) & 255
        oct3 = (ip_int >> 8) & 255
        oct4 = ip_int & 255
        ip_str = f"{oct1}.{oct2}.{oct3}.{oct4}"
        ip_obj = IPv4Address(ip_int)

        # Now this section needs to run in multithread 16x 
        if is_public(ip_obj):
            bind = f"{defstr} {ip_obj}"
            output = net_exec(bind)
            current_time = datetime.now()
            file_name = f"{NT_DATAROOT}netcrawler/netcrawler_enum_ip-{ip_obj}-{current_time}.xml"
            with open(file_name, "a") as file: 
                file.write(output["stdout"])
                file.write(search_ci_badguys(ip_obj))
            net_logger(f"[info] Report for {ip_obj} is done!", "green", "bold")