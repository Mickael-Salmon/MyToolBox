import os
import subprocess
import socket
import psutil
import ipaddress
import requests
import re
import time

from colorama import Fore, init
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.prompt import Prompt
from rich import box

console = Console()

init(autoreset=True)

def check_if_wireless(interface):
    wireless_exists = os.path.exists(f'/sys/class/net/{interface}/wireless')
    if wireless_exists:
        console.print(f"L'interface [bold green]{escape(interface)}[/bold green] est sans fil 📶")
    else:
        console.print(f"L'interface [bold red]{escape(interface)}[/bold red] n'est pas sans fil ❌")

    return wireless_exists

def get_wan_ip():
    try:
        response = requests.get('https://httpbin.org/ip')
        wan_ip = response.json()['origin']
        console.print(f"[bold green]Adresse IP WAN :[/bold green] {escape(wan_ip)} 🌍")
        return wan_ip
    except Exception as e:
        console.print("[bold red]Impossible de récupérer l'adresse IP WAN :[/bold red] Indisponible ❌", style="red")
        return "Indisponible"

def get_os_info():
    try:
        with open('/etc/os-release') as f:
            lines = f.readlines()
        os_info = {line.split('=')[0]: line.split('=')[1].strip().strip('"') for line in lines if '=' in line}
        name = os_info.get('NAME', 'Indisponible')
        version = os_info.get('VERSION_ID', 'Indisponible')
        formatted_os_info = f"{name} ({version})"
        console.print(f"[bold green]Système d'exploitation:[/bold green] {escape(formatted_os_info)} 💻")
        return formatted_os_info
    except FileNotFoundError:
        console.print("[bold red]Informations sur la distribution indisponibles[/bold red] ❌", style="red")
        return "Informations sur la distribution indisponibles"

def check_docker():
    try:
        subprocess.run(['docker', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = subprocess.check_output(['docker', 'ps'], text=True).strip()
        if output:
            table = Table(title="Conteneurs Docker en cours d'exécution", box=box.ROUNDED)
            headers = output.splitlines()[0].split()
            for header in headers:
                table.add_column(header, style="magenta")
            for row in output.splitlines()[1:]:
                table.add_row(*row.split(maxsplit=len(headers)-1))
            console.print(table)
            return f"Docker est installé. Conteneurs en cours d'exécution :\n{output}"
        else:
            console.print("Docker est installé, mais aucun conteneur n'est en cours d'exécution.", style="yellow")
            return "Docker est installé, mais aucun conteneur n'est en cours d'exécution."
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("Docker n'est pas installé ou non accessible.", style="red")
        return "Docker n'est pas installé ou non accessible."

def print_system_info():
    table = Table(title="Informations sur le système", box=box.ROUNDED)

    table.add_column("Description", justify="right", style="cyan", no_wrap=True)
    table.add_column("Valeur", style="magenta")

    try:
        cpu_count = psutil.cpu_count()
        memory_info = psutil.virtual_memory()
        disk_usage = psutil.disk_usage('/')

        table.add_row("Nombre de CPU", str(cpu_count) + " 💻")
        table.add_row("Utilisation de la mémoire", f"{memory_info.percent}% 🧠")
        table.add_row("Utilisation du disque", f"{disk_usage.percent}% 💾")
    except Exception as e:
        console.print(f"[bold red]Erreur lors de la récupération des informations système:[/bold red] {e}", style="red")

    console.print(table)

def list_users():
    with open('/etc/passwd', 'r') as f:
        lines = f.readlines()

    table = Table(title="Utilisateurs du système", box=box.ROUNDED)
    table.add_column("Nom d'utilisateur", style="cyan")

    for line in lines:
        username = line.split(':')[0]
        table.add_row(username)

    console.print(table)

def list_logged_in_users():
    try:
        output = subprocess.check_output('who', shell=True, text=True).strip().split('\n')
        logged_in_users = list(set([line.split()[0] for line in output]))  # Enlever les doublons

        if logged_in_users:
            table = Table(title="Utilisateurs actuellement connectés", box=box.ROUNDED)
            table.add_column("Nom d'utilisateur", style="cyan")

            for user in logged_in_users:
                table.add_row(user)

            console.print(table)
        else:
            console.print("Aucun utilisateur connecté.", style="yellow")
    except subprocess.CalledProcessError:
        console.print("Impossible de récupérer la liste des utilisateurs connectés.", style="red")

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

    table = Table(title="Bande passante actuelle", box=box.ROUNDED)
    table.add_column("Type", style="cyan")
    table.add_column("Valeur (Mbps)", style="magenta")

    table.add_row("Trafic entrant", f"{current_in_Mbps:.2f} Mbps ⬇️")
    table.add_row("Trafic sortant", f"{current_out_Mbps:.2f} Mbps ⬆️")

    console.print(table)

def check_snap_and_flatpak():
    info = {}

    # Pour Snap
    try:
        subprocess.run(['snap', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        snap_output = subprocess.check_output('snap list', shell=True, text=True).strip().split('\n')
        snap_headers = snap_output[0].split()

        snap_table = Table(title="Snap Packages", box=box.ROUNDED)
        for header in snap_headers:
            snap_table.add_column(header, style="cyan")

        for row in snap_output[1:]:
            snap_table.add_row(*row.split(maxsplit=len(snap_headers)-1))

        info['snap'] = snap_table
    except (subprocess.CalledProcessError, FileNotFoundError):
        info['snap'] = 'Non installé'

    # Pour Flatpak
    try:
        subprocess.run(['flatpak', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        flatpak_output = subprocess.check_output('flatpak list', shell=True, text=True).strip().split('\n')
        flatpak_headers = ["Application", "Branch", "Numéro de version"]

        flatpak_table = Table(title="Flatpak Applications", box=box.ROUNDED)
        for header in flatpak_headers:
            flatpak_table.add_column(header, style="magenta")

        for row in flatpak_output:
            try:
                parts = row.split()
                app = parts[0]
                branch = parts[-2]
                version_number = parts[-3]
                flatpak_table.add_row(app, branch, version_number)
            except (ValueError, IndexError):
                flatpak_table.add_row(row, 'Inconnu', 'Inconnu')

        info['flatpak'] = flatpak_table
    except (subprocess.CalledProcessError, FileNotFoundError):
        info['flatpak'] = 'Non installé'

    # Affichage des tableaux
    for key, table in info.items():
        if isinstance(table, Table):
            console.print(table)
        else:
            console.print(f"{key.capitalize()} : {table}", style="yellow")

def run_and_print(cmd, desc):
    console.print(f"{desc}:", style="bold yellow")
    try:
        output = subprocess.check_output(cmd, shell=True, text=True).strip()
        console.print(output, style="bold cyan")
    except subprocess.CalledProcessError:
        console.print("Erreur lors de l'exécution de la commande.", style="bold red")
    console.print("-" * 40)

def get_network_info():
    console.print("Hello Friend! Voici les informations réseau et système de cette machine:\n", style="bold green")

    run_and_print('hostname', 'Nom de la machine')
    run_and_print('uname -a', 'Informations sur le noyau')

    console.print("Informations sur la distribution:", style="bold yellow")
    # Ici, appelle ta fonction modifiée `get_os_info` avec `rich`
    get_os_info()  # Assure-toi que cette fonction utilise `rich` pour l'affichage

    run_and_print('ip route | grep default', 'Route par défaut')
    run_and_print('route -n', 'Table de routage')
    run_and_print('cat /etc/resolv.conf | grep nameserver', 'DNS')
    run_and_print('netstat -tuln', 'Connexions actives')

    # Affichage des adresses IP
    ips = subprocess.check_output('hostname -I', shell=True, text=True).strip().split()
    lan_ipv4 = [ip for ip in ips if ipaddress.ip_address(ip).is_private and ':' not in ip]
    lan_ipv6 = [ip for ip in ips if ipaddress.ip_address(ip).is_private and ':' in ip]
    wan_ip = get_wan_ip()  # Cette fonction doit également utiliser `rich`

    console.print("Adresses IP:", style="bold yellow")
    console.print(f"LAN IPv4: {', '.join(lan_ipv4)}", style="bold cyan")
    console.print(f"LAN IPv6: {', '.join(lan_ipv6)}", style="bold cyan")
    console.print(f"WAN IP: {wan_ip}", style="bold cyan")
    console.print("-" * 40)

def check_security():
    console.print("\n[bold blue]Vérification de la Sécurité[/bold blue]")

    # Vérification de l'état de UFW (Uncomplicated Firewall)
    try:
        ufw_status = subprocess.check_output("sudo ufw status", shell=True, text=True).strip()
        console.print(f"État du Firewall (UFW): [bold green]{ufw_status}[/bold green]")
    except subprocess.CalledProcessError:
        console.print("Firewall (UFW) non installé ou erreur lors de la vérification.", style="bold red")

    # Vérification de l'état de firewalld
    try:
        firewalld_status = subprocess.check_output("sudo systemctl is-active firewalld", shell=True, text=True).strip()
        if firewalld_status == "active":
            console.print("Firewall (firewalld): [bold green]Actif[/bold green]")
        else:
            console.print("Firewall (firewalld): [bold red]Inactif ou non installé[/bold red]")
    except subprocess.CalledProcessError:
        console.print("Erreur lors de la vérification de firewalld.", style="bold red")

    # Vérification de l'état du service SSH
    try:
        ssh_status = subprocess.check_output("sudo systemctl is-active ssh", shell=True, text=True).strip()
        if ssh_status == "active":
            console.print("Service SSH: [bold green]Actif[/bold green]")
        else:
            console.print("Service SSH: [bold red]Inactif[/bold red]")
    except subprocess.CalledProcessError:
        console.print("SSH non installé ou erreur lors de la vérification.", style="bold red")

    console.print("-" * 40)



def main_menu():
    table = Table(title="🚀 Menu Principal 🚀", box=box.ROUNDED, show_header=True, header_style="bold blue")
    table.add_column("Option", style="dim", width=12)
    table.add_column("Description", justify="left")

    menu_items = {
        "1": "📡 Vérifier si une interface est sans fil",
        "2": "🌐 Obtenir l'adresse IP WAN",
        "3": "💻 Afficher les informations du système d'exploitation",
        "4": "🐳 Vérifier Docker",
        "5": "🔍 Afficher les informations système",
        "6": "👥 Lister les utilisateurs du système",
        "7": "👤 Lister les utilisateurs connectés",
        "8": "📊 Afficher la bande passante",
        "9": "📦 Vérifier Snap et Flatpak",
        "10": "🌐 Afficher les informations réseau",
        "11": "🔒 Vérifier la sécurité (Firewall et SSH)",
        "0": "🚪 Quitter"
    }

    for key, desc in menu_items.items():
        table.add_row(key, desc)

    console.print(table)

    choice = Prompt.ask("👉 Choisis une option", default="0")

    if choice == "1":
        interface = Prompt.ask("💻 Entrez le nom de l'interface")
        check_if_wireless(interface)
    elif choice == "2":
        get_wan_ip()
    elif choice == "3":
        get_os_info()
    elif choice == "4":
        check_docker()
    elif choice == "5":
        print_system_info()
    elif choice == "6":
        list_users()
    elif choice == "7":
        list_logged_in_users()
    elif choice == "8":
        get_bandwidth()
    elif choice == "9":
        check_snap_and_flatpak()
    elif choice == "10":
        get_network_info()
    elif choice == "11":
        check_security()
    elif choice == "0":
        console.print("👋 Au revoir !", style="bold green")
        exit()
    else:
        console.print("🔴 Choix invalide, veuillez réessayer", style="bold red")

    if choice != "0":
        main_menu()


if __name__ == "__main__":
    main_menu()