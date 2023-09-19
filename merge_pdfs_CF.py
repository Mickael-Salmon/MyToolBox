import argparse
import os
from PyPDF2 import PdfMerger
from colorama import Fore, init
from tqdm import tqdm

init(autoreset=True)

def merge_pdfs_in_current_folder(output_filename, folder='.'):
    os.chdir(folder)
    pdf_files = [f for f in os.listdir() if f.endswith('.pdf')]
    pdf_files.sort()

    if len(pdf_files) == 0:
        print(Fore.RED + "Aucun fichier PDF trouvé dans le dossier courant.")
        return

    print(Fore.GREEN + f"{len(pdf_files)} fichiers PDF trouvés. Fusion en cours...")

    merger = PdfMerger()
    try:
        for pdf in tqdm(pdf_files, desc="Fusion des PDFs", unit="fichier"):
            merger.append(pdf)
    except Exception as e:
        print(Fore.RED + f"Erreur lors de la fusion : {e}")
        return

    merger.write(output_filename)
    merger.close()

    print(Fore.GREEN + f"La fusion est terminée. Le fichier résultant est {output_filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fusionne tous les fichiers PDF dans le dossier spécifié.")
    parser.add_argument("-o", "--output", help="Nom du fichier PDF de sortie", default="fichier_fusionne.pdf")
    parser.add_argument("-f", "--folder", help="Dossier où chercher les fichiers PDF", default=".")

    args = parser.parse_args()
    merge_pdfs_in_current_folder(args.output, args.folder)
