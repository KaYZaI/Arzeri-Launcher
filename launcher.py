import customtkinter as ctk
import requests
import os
import sys
import json
import ctypes
import subprocess
from PIL import Image, ImageDraw, ImageFont

def resource_path(relative_path):
    """Obtient le chemin absolu des ressources pour PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# --- GÉNÉRATION DES TEXTURES FUSIONNÉES AVEC LE FOND ---
def creer_texture_cadre(largeur, hauteur, couleur_accent, bg_crop=None, survol=False, texte=""):
    if bg_crop is not None:
        base = bg_crop.convert("RGBA").resize((largeur, hauteur), Image.Resampling.LANCZOS)
    else:
        base = Image.new("RGBA", (largeur, hauteur), (20, 20, 20, 255))
        
    calque = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
    draw = ImageDraw.Draw(calque)
    
    couleur_fond = (20, 32, 52, 215) if survol else (12, 19, 32, 200)
    bordure_sombre = (5, 10, 18, 235)
    rayon = 5

    # 1. Accent lumineux (décalé de 2px à gauche et en bas)
    draw.rounded_rectangle([0, 2, largeur - 2, hauteur], radius=rayon, fill=couleur_accent)
    
    # 2. Corps principal semi-transparent
    draw.rounded_rectangle([3, 0, largeur, hauteur - 3], radius=rayon, fill=couleur_fond, outline=bordure_sombre, width=1)
    
    # 3. Texte optionnel
    if texte:
        try:
            font = ImageFont.truetype("segoeui.ttf", 16)
        except Exception:
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), texte.upper(), font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        x_text = 3 + (largeur - 3 - text_w) / 2
        y_text = (hauteur - 3 - text_h) / 2 - 2
        draw.text((x_text, y_text), texte.upper(), font=font, fill=(240, 245, 255, 255))
        
    resultat = Image.alpha_composite(base, calque)
    return ctk.CTkImage(light_image=resultat, dark_image=resultat, size=(largeur, hauteur))

class BoutonGodot(ctk.CTkLabel):
    def __init__(self, master, text="", width=200, height=50, bg_crop=None, command=None, **kwargs):
        self.w = width
        self.h = height
        self.texte = text
        self.bg_crop = bg_crop
        self.command = command
        self.actif = True
        
        self.img_normal = creer_texture_cadre(self.w, self.h, (68, 145, 185, 255), self.bg_crop, survol=False, texte=self.texte)
        self.img_survol = creer_texture_cadre(self.w, self.h, (100, 195, 235, 255), self.bg_crop, survol=True, texte=self.texte)
        
        super().__init__(master, text="", image=self.img_normal, width=self.w, height=self.h, cursor="hand2", **kwargs)
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, event):
        if self.actif:
            super().configure(image=self.img_survol)

    def _on_leave(self, event):
        if self.actif:
            super().configure(image=self.img_normal)

    def _on_click(self, event):
        if self.actif and self.command:
            self.command()

    def configure(self, **kwargs):
        if "text" in kwargs:
            self.texte = kwargs.pop("text")
            self.img_normal = creer_texture_cadre(self.w, self.h, (68, 145, 185, 255), self.bg_crop, survol=False, texte=self.texte)
            self.img_survol = creer_texture_cadre(self.w, self.h, (100, 195, 235, 255), self.bg_crop, survol=True, texte=self.texte)
            super().configure(image=self.img_normal)
        if "command" in kwargs:
            self.command = kwargs.pop("command")
        if "state" in kwargs:
            state = kwargs.pop("state")
            self.actif = (state != "disabled")
            super().configure(cursor="hand2" if self.actif else "arrow")
        if kwargs:
            super().configure(**kwargs)

class PanneauProgressionGodot(ctk.CTkLabel):
    def __init__(self, master, width=450, height=80, bg_crop=None, **kwargs):
        self.bg_tex = creer_texture_cadre(width, height, (235, 185, 52, 255), bg_crop, survol=False)
        super().__init__(master, text="", image=self.bg_tex, width=width, height=height, **kwargs)
        
        self.label = ctk.CTkLabel(
            self, text="Téléchargement : 0%", font=("Segoe UI", 15, "bold"),
            text_color="#f0f5ff", fg_color="#0c1320"
        )
        self.label.place(relx=0.5, rely=0.32, anchor="center")
        
        self.bar = ctk.CTkProgressBar(
            self, width=380, height=12, corner_radius=3,
            fg_color="#070b14", progress_color="#ebb934",
            border_width=1, border_color="#5c4814"
        )
        self.bar.place(relx=0.5, rely=0.68, anchor="center")

# --- CONFIGURATION ---
REPO_URL = "https://api.github.com/repos/KaYZaI/Arzeri-Ascended-Releases/releases/latest"
GAME_NAME = "Arzeri"
INSTALL_DIR = os.path.join(os.getenv('LOCALAPPDATA'), GAME_NAME)
VERSION_FILE = os.path.join(INSTALL_DIR, "version.json")
GAME_EXE = os.path.join(INSTALL_DIR, "Arzeri.exe")

os.makedirs(INSTALL_DIR, exist_ok=True)

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
            if asset["name"].endswith(".exe"):
                download_url = asset["browser_download_url"]
                break
                
        if not download_url:
            raise Exception("Aucun fichier .exe trouvé dans la release.")

        local_version = get_local_version()
        
        if local_version != latest_version:
            if local_version == "v0.0.0":
                btn_action.configure(text="Télécharger", command=lambda: download_game(download_url, latest_version))
            else:
                btn_action.configure(text="Mettre à jour", command=lambda: download_game(download_url, latest_version))
        else:
            btn_action.configure(text="Jouer", command=launch_game)
            
    except Exception as e:
        if os.path.exists(GAME_EXE):
            btn_action.configure(text="Jouer (Hors-ligne)", command=launch_game)
        else:
            btn_action.configure(text="Erreur de connexion", state="disabled")

def download_game(url, new_version):
    btn_action.place_forget()
    progress_frame.place(x=prog_x, y=prog_y)
    progress_frame.bar.set(0)
    progress_frame.label.configure(text="Téléchargement : 0%")
    app.update()
    
    temp_exe = GAME_EXE + ".tmp"
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 
        downloaded = 0
        
        with open(temp_exe, "wb") as f:
            for data in response.iter_content(block_size):
                f.write(data)
                downloaded += len(data)
                if total_size > 0:
                    percent = downloaded / total_size
                    progress_frame.bar.set(percent)
                    progress_frame.label.configure(text=f"Téléchargement : {int(percent * 100)}%")
                    app.update()
        
        if os.path.exists(GAME_EXE):
            os.remove(GAME_EXE)
        os.rename(temp_exe, GAME_EXE)
            
        with open(VERSION_FILE, "w") as f:
            json.dump({"version": new_version}, f)
            
        progress_frame.place_forget()
        btn_action.place(x=btn_x, y=btn_y)
        btn_action.configure(text="Jouer", state="normal", command=launch_game)
        
    except Exception as e:
        if os.path.exists(temp_exe):
            os.remove(temp_exe)
        progress_frame.place_forget()
        btn_action.place(x=btn_x, y=btn_y)
        btn_action.configure(text="Erreur, réessayez", state="normal", command=check_update)

def launch_game():
    if os.path.exists(GAME_EXE):
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen([GAME_EXE], cwd=INSTALL_DIR, creationflags=DETACHED_PROCESS)
        app.destroy()

# --- INTERFACE GRAPHIQUE ---
app = ctk.CTk()

window_width = 800
window_height = 450

screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

x = int((screen_width / 2) - (window_width / 2))
y = int((screen_height / 2) - (window_height / 2))

app.geometry(f"{window_width}x{window_height}+{x}+{y}")
app.title("Arzéri Launcher")
app.resizable(False, False)  # Bloque le redimensionnement et le plein écran

try:
    app.iconbitmap(resource_path("icon.ico"))
except Exception:
    pass

# Coordonnées exactes (équivalentes à relx=0.5, rely=0.8, anchor="center" sur 800x450)
btn_w, btn_h = 200, 50
btn_x = int(window_width * 0.5 - btn_w / 2)   # 300
btn_y = int(window_height * 0.8 - btn_h / 2)  # 335

prog_w, prog_h = 450, 80
prog_x = int(window_width * 0.5 - prog_w / 2)   # 175
prog_y = int(window_height * 0.8 - prog_h / 2)  # 320

btn_bg_crop = None
prog_bg_crop = None

try:
    raw_bg = Image.open(resource_path("background.png")).resize((window_width, window_height), Image.Resampling.LANCZOS)
    bg_image = ctk.CTkImage(light_image=raw_bg, dark_image=raw_bg, size=(window_width, window_height))
    bg_label = ctk.CTkLabel(app, image=bg_image, text="")
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    
    btn_bg_crop = raw_bg.crop((btn_x, btn_y, btn_x + btn_w, btn_y + btn_h))
    prog_bg_crop = raw_bg.crop((prog_x, prog_y, prog_x + prog_w, prog_y + prog_h))
except Exception:
    pass

# Bouton d'action sans fond carré noir
btn_action = BoutonGodot(app, text="Vérification...", width=btn_w, height=btn_h, bg_crop=btn_bg_crop)
btn_action.place(x=btn_x, y=btn_y)

# Panneau de téléchargement style Godot jaune/or sans fond carré noir
progress_frame = PanneauProgressionGodot(app, width=prog_w, height=prog_h, bg_crop=prog_bg_crop)

app.after(100, check_update)
app.mainloop()