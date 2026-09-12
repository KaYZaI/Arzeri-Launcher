import customtkinter as ctk
import requests
import zipfile
import io
import os
import sys
import json
import ctypes
import subprocess
from PIL import Image

def resource_path(relative_path):
    """Obtient le chemin absolu des ressources pour PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# --- CONFIGURATION ---
REPO_URL = "https://api.github.com/repos/KaYZaI/Arzeri-Ascended-Releases/releases/latest"
GAME_NAME = "Arzeri_Ascended"
INSTALL_DIR = os.path.join(os.getenv('LOCALAPPDATA'), GAME_NAME)
VERSION_FILE = os.path.join(INSTALL_DIR, "version.json")
GAME_EXE = os.path.join(INSTALL_DIR, "Game.exe")

os.makedirs(INSTALL_DIR, exist_ok=True)

# Forcer l'icône dans la barre des tâches sous Windows
myappid = 'kayzai.arzeri.launcher.1.0'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def get_local_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return json.load(f).get("version", "v0.0.0")
    return "v0.0.0"

def check_update():
    try:
        response = requests.get(REPO_URL)
        response.raise_for_status()
        latest_data = response.json()
        latest_version = latest_data["tag_name"]
        
        download_url = None
        for asset in latest_data.get("assets", []):
            if asset["name"].endswith(".zip"):
                download_url = asset["browser_download_url"]
                break
                
        if not download_url:
            raise Exception("Aucun fichier .zip trouvé dans la release.")

        local_version = get_local_version()
        
        if local_version != latest_version:
            if local_version == "v0.0.0":
                btn_action.configure(text="Télécharger", command=lambda: download_and_extract(download_url, latest_version))
            else:
                btn_action.configure(text="Mettre à jour", command=lambda: download_and_extract(download_url, latest_version))
        else:
            btn_action.configure(text="Jouer", command=launch_game)
            
    except Exception as e:
        if os.path.exists(GAME_EXE):
            btn_action.configure(text="Jouer (Hors-ligne)", command=launch_game)
        else:
            btn_action.configure(text="Erreur de connexion", state="disabled")

def download_and_extract(url, new_version):
    btn_action.place_forget()
    # Affichage du panneau
    progress_frame.place(relx=0.5, rely=0.8, anchor="center")
    progress_bar.set(0)
    app.update()
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 
        zip_data = io.BytesIO()
        downloaded = 0
        
        for data in response.iter_content(block_size):
            zip_data.write(data)
            downloaded += len(data)
            if total_size > 0:
                percent = downloaded / total_size
                progress_bar.set(percent)
                progress_label.configure(text=f"Téléchargement : {int(percent * 100)}%")
                app.update()
        
        progress_label.configure(text="Extraction en cours...")
        app.update()
        
        with zipfile.ZipFile(zip_data) as zip_ref:
            zip_ref.extractall(INSTALL_DIR)
            
        with open(VERSION_FILE, "w") as f:
            json.dump({"version": new_version}, f)
            
        # Fin : on cache le panneau et remet le bouton
        progress_frame.place_forget()
        btn_action.place(relx=0.5, rely=0.8, anchor="center")
        btn_action.configure(text="Jouer", state="normal", command=launch_game)
        
    except Exception as e:
        progress_frame.place_forget()
        btn_action.place(relx=0.5, rely=0.8, anchor="center")
        btn_action.configure(text="Erreur, réessayez", state="normal", command=check_update)

def launch_game():
    if os.path.exists(GAME_EXE):
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen([GAME_EXE], cwd=INSTALL_DIR, creationflags=DETACHED_PROCESS)
        app.destroy()

# --- INTERFACE GRAPHIQUE ---
app = ctk.CTk()

# Dimensions de la fenêtre de ton launcher
window_width = 800
window_height = 450

# Récupération de la taille de l'écran du joueur
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

# Calcul des coordonnées exactes pour le centre
x = int((screen_width / 2) - (window_width / 2))
y = int((screen_height / 2) - (window_height / 2))

# Application de la taille et de la position (+x+y)
app.geometry(f"{window_width}x{window_height}+{x}+{y}")
app.title("Arzéri Launcher")

try:
    app.iconbitmap(resource_path("icon.ico"))
except Exception:
    pass

try:
    bg_image = ctk.CTkImage(Image.open(resource_path("background.png")), size=(800, 450))
    bg_label = ctk.CTkLabel(app, image=bg_image, text="")
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
except Exception:
    pass

# Bouton d'action avec angles droits pour éviter les coins noirs
btn_action = ctk.CTkButton(app, text="Vérification...", width=200, height=50, font=("Arial", 20, "bold"), corner_radius=0, border_width=1, border_color="#3498db")
btn_action.place(relx=0.5, rely=0.8, anchor="center")

# Panneau de téléchargement avec angles droits (corner_radius=0) pour éviter le bug de transparence, avec une fine bordure
progress_frame = ctk.CTkFrame(app, width=450, height=80, fg_color="#1e1e1e", corner_radius=0, border_width=1, border_color="#3498db")
progress_frame.pack_propagate(False)

progress_label = ctk.CTkLabel(progress_frame, text="Téléchargement : 0%", font=("Arial", 16, "bold"), text_color="white")
progress_label.place(relx=0.5, rely=0.3, anchor="center")

progress_bar = ctk.CTkProgressBar(progress_frame, width=380, progress_color="#3498db")
progress_bar.place(relx=0.5, rely=0.7, anchor="center")

app.after(100, check_update)
app.mainloop()