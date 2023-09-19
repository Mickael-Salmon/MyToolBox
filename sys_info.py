import os
import subprocess
import socket
import psutil
import ipaddress
import requests
import re
import psutil
import time

from colorama import Fore, init

init(autoreset=True)

def check_if_wireless(interface):
    return os.path.exists(f'/sys/class/net/{interface}/wireless')

def get_wan_ip():
    try:
        response = requests.get('https://httpbin.org/ip')
        return response.json()['origin']
    except Exception:
        return "Indisponible"

def get_os_info():
    try:
        with open('/etc/os-release') as f:
            lines = f.readlines()
        os_info = {line.split('=')[0]: line.split('=')[1].strip().strip('"') for line in lines if '=' in line}
        return f"{os_info.get('NAME', 'Indisponible')} ({os_info.get('VERSION_ID', 'Indisponible')})"
    except FileNotFoundError:
        return "Informations sur la distribution indisponibles"

def check_docker():
    try:
        subprocess.run(['docker', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = subprocess.check_output(['docker', 'ps'], text=True).strip()
        if output:
            return f"Docker est installé. Conteneurs en cours d'exécution :\n{output}"
        else:
            return "Docker est installé, mais aucun conteneur n'est en cours d'exécution."
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "Docker n'est pas installé ou non accessible."

def get_system_info():
    cpu_count = psutil.cpu_count()
    memory_info = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')

    print(Fore.YELLOW + "Informations sur le système:")
    print(Fore.CYAN + f"Nombre de CPU : {cpu_count}")
    print(Fore.CYAN + f"Utilisation de la mémoire : {memory_info.percent}%")
    print(Fore.CYAN + f"Utilisation du disque : {disk_usage.percent}%")
    print(Fore.RESET + "-" * 40)

def list_users():
    with open('/etc/passwd', 'r') as f:
        lines = f.readlines()
    users = [line.split(':')[0] for line in lines]
    return users

def list_logged_in_users():
    try:
        output = subprocess.check_output('who', shell=True, text=True).strip().split('\n')
        logged_in_users = [line.split()[0] for line in output]
        return list(set(logged_in_users))  # Enlever les doublons
    except subprocess.CalledProcessError:
        return []

def get_bandwidth():
    net1_out = psutil.net_io_counters().bytes_sent
    net1_in = psutil.net_io_counters().bytes_recv
    time.sleep(1)
    net2_out = psutil.net_io_counters().bytes_sent
    net2_in = psutil.net_io_counters().bytes_recv

    current_in = net2_in - net1_in if net1_in <= net2_in else 0
    current_out = net2_out - net1_out if net1_out <= net2_out else 0

    # Conversion en Mbps (1 Byte = 8 bits, 1 Mbps = 1e6 bits)
    current_in_Mbps = (current_in * 8) / 1e6
    current_out_Mbps = (current_out * 8) / 1e6

    return {"traffic_in": current_in_Mbps, "traffic_out": current_out_Mbps}



def format_as_table(rows, headers):
    """Formate une liste de dictionnaires comme un tableau ASCII."""
    # Trouver la largeur maximale pour chaque colonne
    col_widths = {header: max(len(str(row.get(header, ""))) for row in rows) for header in headers}
    # Créer la ligne de séparation
    separator = '+'.join(['-' * (col_widths[header] + 2) for header in headers])
    # Créer le format pour chaque ligne du tableau
    row_format = "| " + " | ".join(["{:>" + str(col_widths[header]) + "}" for header in headers]) + " |"

    table = ["+" + separator + "+"]
    # Ajouter l'en-tête
    table.append(row_format.format(*headers))
    table.append("+" + separator + "+")
    # Ajouter les lignes de données
    for row in rows:
        table.append(row_format.format(*[row.get(header, "") for header in headers]))
        table.append("+" + separator + "+")
    return "\n".join(table)

def check_snap_and_flatpak():
    info = {}

    # Pour Snap
    try:
        subprocess.run(['snap', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        snap_output = subprocess.check_output('snap list', shell=True, text=True).strip().split('\n')
        snap_headers = snap_output[0].split()
        snap_rows = [dict(zip(snap_headers, row.split())) for row in snap_output[1:]]
        snap_table = format_as_table(snap_rows, snap_headers)
        info['snap'] = snap_table
    except (subprocess.CalledProcessError, FileNotFoundError):
        info['snap'] = 'Non installé'

    # Pour Flatpak
    try:
        subprocess.run(['flatpak', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        flatpak_output = subprocess.check_output('flatpak list', shell=True, text=True).strip().split('\n')
        flatpak_headers = ["Application", "Branch", "Numéro de version"]
        flatpak_rows = []
        for row in flatpak_output:
            try:
                parts = row.split()
                app = parts[0]
                branch = parts[-2]
                version_number = parts[-3]
                flatpak_rows.append({'Application': app, 'Branch': branch, 'Numéro de version': version_number})
            except (ValueError, IndexError):
                flatpak_rows.append({'Application': row, 'Branch': 'Inconnu', 'Numéro de version': 'Inconnu'})
        flatpak_table = format_as_table(flatpak_rows, flatpak_headers)
        info['flatpak'] = flatpak_table
    except (subprocess.CalledProcessError, FileNotFoundError):
        info['flatpak'] = 'Non installé'


    return info



def get_network_info():
    print(Fore.GREEN + "Hello Friend! Voici les informations réseau et système de cette machine:\n")

    def run_and_print(cmd, desc):
        print(Fore.YELLOW + f"{desc}:")
        try:
            output = subprocess.check_output(cmd, shell=True, text=True).strip()
            print(Fore.CYAN + output)
        except subprocess.CalledProcessError:
            print(Fore.RED + "Erreur lors de l'exécution de la commande.")
        print(Fore.RESET + "-" * 40)


    run_and_print('hostname', 'Nom de la machine')
    run_and_print('uname -a', 'Informations sur le noyau')

    print(Fore.YELLOW + "Informations sur la distribution:")
    print(Fore.CYAN + get_os_info())
    print(Fore.RESET + "-" * 40)

    run_and_print('ip route | grep default', 'Route par défaut')
    run_and_print('route -n', 'Table de routage')
    run_and_print('cat /etc/resolv.conf | grep nameserver', 'DNS')
    run_and_print('netstat -tuln', 'Connexions actives')

    ips = subprocess.check_output('hostname -I', shell=True, text=True).strip().split()
    lan_ipv4 = [ip for ip in ips if ipaddress.ip_address(ip).is_private and ':' not in ip]
    lan_ipv6 = [ip for ip in ips if ipaddress.ip_address(ip).is_private and ':' in ip]
    wan_ip = get_wan_ip()

    print(Fore.YELLOW + "Adresses IP:")
    print(Fore.CYAN + f"LAN IPv4: {', '.join(lan_ipv4)}")
    print(Fore.CYAN + f"LAN IPv6: {', '.join(lan_ipv6)}")
    print(Fore.CYAN + f"WAN IP: {wan_ip}")
    print(Fore.RESET + "-" * 40)
    print(Fore.YELLOW + "Vérification de Docker:")
    print(Fore.CYAN + check_docker())
    print(Fore.RESET + "-" * 40)
    bandwidth = get_bandwidth()
    print(f"Bande passante entrante : {bandwidth['traffic_in']:.2f} Mbps")
    print(f"Bande passante sortante : {bandwidth['traffic_out']:.2f} Mbps")
    print(Fore.YELLOW + "Informations sur la bande passante (si speedtest-cli est installé):")
    try:
        output = subprocess.check_output('speedtest-cli --simple', shell=True, text=True).strip()
        print(Fore.CYAN + output)
    except subprocess.CalledProcessError:
        print(Fore.RED + "Indisponible.")
    print(Fore.RESET + "-" * 40)

    run_and_print('df -h', 'Disques et partages réseau montés')

    print(Fore.YELLOW + "Tâches planifiées:")
    try:
        output = subprocess.check_output('crontab -l', shell=True, text=True).strip()
        print(Fore.CYAN + output)
    except subprocess.CalledProcessError:
        print(Fore.RED + "Pas de tâches planifiées ou indisponibles.")
    print(Fore.RESET + "-" * 40)

    # Appel à la nouvelle fonction pour afficher les informations sur le système
    get_system_info()

    print(Fore.YELLOW + "Utilisateurs présents sur le système:")
    print(Fore.CYAN + ", ".join(list_users()))
    print(Fore.RESET + "-" * 40)

    print(Fore.YELLOW + "Utilisateurs actuellement connectés:")
    logged_in_users = list_logged_in_users()
    if logged_in_users:
        print(Fore.CYAN + ", ".join(logged_in_users))
    else:
        print(Fore.RED + "Aucun utilisateur connecté.")
    print(Fore.RESET + "-" * 40)

    print(Fore.YELLOW + "Vérification de Snap et Flatpak :")
    packaging_info = check_snap_and_flatpak()
    for package_system, output in packaging_info.items():
        if output != 'Non installé':
            print(Fore.CYAN + f"{package_system.capitalize()} est installé. Applications :\n{output}")
        else:
            print(Fore.RED + f"{package_system.capitalize()} n'est pas installé.")
    print(Fore.RESET + "-" * 40)




if __name__ == "__main__":
    get_network_info()
