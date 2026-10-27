# -*- coding: utf-8 -*-
"""
3DS RAM Unlock Patcher
Arrastra un 0000.XXXXXXXX.app (sacado de un .CIA) y aplica el parche de
modo de memoria para OLD 3DS y NEW 3DS.  La salida se guarda junto al programa.
"""
import hashlib
import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog

try:  # arrastrar y soltar (opcional: si falta, queda el boton "Elegir")
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:
    HAS_DND = False

# --------------------------------------------------------------------------
#  Tema: negro / bordes celestes / letras blancas
# --------------------------------------------------------------------------
BG = "#000000"
FG = "#FFFFFF"
CYAN = "#00E5FF"
HOVER = "#06232a"
MUTED = "#8fa3a8"
FONT = ("Segoe UI", 10)
FONT_B = ("Segoe UI", 10, "bold")
FONT_T = ("Segoe UI", 17, "bold")

# --------------------------------------------------------------------------
#  Parche (identico a max.py)
# --------------------------------------------------------------------------
OLD_MODE = 0x3   # OLD 3DS
NEW_MODE = 0x1   # NEW 3DS
HEADER_LEN = 0xA00


class PatchError(Exception):
    def __init__(self, key):
        super().__init__(key)
        self.key = key


def app_dir():
    """Carpeta donde esta el programa (.exe o .py): ahi se guarda la salida."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def tool_path(name):
    """Busca una herramienta incluida (ctrtool / makerom) dentro del .exe o al lado."""
    base = getattr(sys, "_MEIPASS", app_dir())
    for folder in (os.path.join(base, "tools"), base, app_dir()):
        p = os.path.join(folder, name)
        if os.path.isfile(p):
            return p
    return None


def _unique(path):
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{stem}_{i}{ext}"):
        i += 1
    return f"{stem}_{i}{ext}"


def patch_app(src, out_dir):
    """Parchea una copia de `src` en `out_dir`. Devuelve dict con los datos."""
    if os.path.getsize(src) < HEADER_LEN:
        raise PatchError("err_small")
    with open(src, "rb") as f:
        head = f.read(HEADER_LEN)

    if head[0x100:0x104] != b"NCCH":
        raise PatchError("err_magic")
    if int.from_bytes(head[0x180:0x184], "little") != 0x400:
        raise PatchError("err_noexh")
    # El ExHeader tiene que estar descifrado (flag NoCrypto o nombre legible).
    title = head[0x200:0x208].rstrip(b"\x00")
    readable = len(title) > 0 and all(32 <= c < 127 for c in title)
    if not (head[0x18F] & 0x04) and not readable:
        raise PatchError("err_crypto")

    before = (head[0x40E] >> 4, head[0x40D] & 0x0F)

    d = bytearray(head)
    for base in (0x400, 0x800):
        d[base + 0x0E] = (d[base + 0x0E] & 0x0F) | (OLD_MODE << 4)
        d[base + 0x0D] = (d[base + 0x0D] & 0xF0) | NEW_MODE
    d[0x160:0x180] = hashlib.sha256(d[0x200:0x600]).digest()

    stem = os.path.splitext(os.path.basename(src))[0]
    out = _unique(os.path.join(out_dir, stem + "_max.app"))
    try:
        shutil.copyfile(src, out)
        with open(out, "r+b") as f:
            f.write(bytes(d))
        # verificacion
        with open(out, "rb") as f:
            chk = f.read(HEADER_LEN)
        ok = (
            chk[0x160:0x180] == hashlib.sha256(chk[0x200:0x600]).digest()
            and all(chk[b + 0x0E] >> 4 == OLD_MODE and chk[b + 0x0D] & 0x0F == NEW_MODE
                    for b in (0x400, 0x800))
        )
        if not ok:
            raise PatchError("err_verify")
    except Exception:
        if os.path.exists(out):
            try:
                os.remove(out)
            except OSError:
                pass
        raise
    return {"out": out, "before": before, "after": (OLD_MODE, NEW_MODE)}


def ctrtool_check(app_file):
    """Pasada extra con ctrtool (si esta incluido). Devuelve lineas utiles o []."""
    exe = tool_path("ctrtool.exe")
    if not exe:
        return []
    try:
        flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        r = subprocess.run([exe, "-t", "ncch", app_file], capture_output=True,
                           text=True, timeout=20, creationflags=flags)
        lines = (r.stdout or "").splitlines()
        return [l.strip() for l in lines
                if any(k in l.lower() for k in ("system mode", "exheader hash"))][:4]
    except Exception:
        return []


# --------------------------------------------------------------------------
#  Textos
# --------------------------------------------------------------------------
LANGS = [("en", "English"), ("es", "Español"), ("pt", "Português")]

T = {
    "en": {
        "title": "3DS RAM Unlock Patcher",
        "lang": "Language",
        "drop": "Drag your 0000.XXXXXXXX.app here\n\nor click to choose it",
        "drop_nodnd": "Click here to choose your 0000.XXXXXXXX.app",
        "browse": "Choose .app",
        "open_out": "Open output folder",
        "help_btn": "Help (F1)",
        "out": "Output folder (same as the program):\n{p}",
        "f1": "Press F1 to see how to get the .app from a .CIA with GodMode9",
        "ftype": "3DS application (*.app)",
        "all": "All files",
        "working": "Patching: {n}",
        "done": "✔ Done → {o}",
        "modes": "   OLD 3DS mode: 0x{a:X} → 0x{b:X}   |   NEW 3DS mode: 0x{c:X} → 0x{d:X}",
        "ctr": "   ctrtool: {l}",
        "err_small": "✘ {n}: the file is too small to be a valid .app.",
        "err_magic": "✘ {n}: not a valid .app (NCCH header not found).",
        "err_noexh": "✘ {n}: this .app has no ExHeader, so it can't be patched.",
        "err_crypto": "✘ {n}: the .app is still encrypted. Decrypt it first (see F1).",
        "err_verify": "✘ {n}: verification of the patched file failed.",
        "err_other": "✘ {n}: error — {e}",
        "help_title": "How to get the .app from a .CIA (GodMode9)",
        "help": (
            "HOW TO EXTRACT THE 0000.XXXXXXXX.app FROM ANY .CIA WITH GODMODE9\n"
            "══════════════════════════════════════════════════════════════\n\n"
            "1. Copy your .cia file to the SD card of your 3DS (any folder).\n\n"
            "2. Power on the console holding START to open GodMode9.\n\n"
            "3. Go to [0:] SDCARD and highlight your .cia file. Press A.\n\n"
            "4. Choose \"Mount image to drive\" (CIA image options).\n\n"
            "5. A virtual drive opens (for example G:). Inside you will see\n"
            "   several files: .tmd, .app, etc.\n"
            "   → The one you need is  0000.XXXXXXXX.app  (index 0000, it is\n"
            "     the game's main content and usually the biggest file).\n\n"
            "6. Highlight it and press Y (copy). Go to  [0:] SDCARD / gm9 / out\n"
            "   (or any folder) and press Y again → \"Copy path here\".\n\n"
            "7. If the .app is encrypted: highlight it, press A →\n"
            "   \"NCCH image options\" → \"Decrypt file (0:/gm9/out)\".\n"
            "   Use the decrypted copy.\n\n"
            "8. Turn the console off, take the SD card out and copy the .app\n"
            "   to your PC.\n\n"
            "9. Drag it onto this program. The patched file\n"
            "   (name_max.app) is created in the same folder as this program.\n\n"
            "Note: the patched .app has an invalid signature, so your console\n"
            "needs custom firmware with signature checks disabled (e.g. Luma3DS)\n"
            "to run it after you put it back into a CIA.\n\n"
            "Press F1 or Esc to close this window."
        ),
    },
    "es": {
        "title": "3DS RAM Unlock Patcher",
        "lang": "Idioma",
        "drop": "Arrastra aquí tu 0000.XXXXXXXX.app\n\no haz clic para elegirlo",
        "drop_nodnd": "Haz clic aquí para elegir tu 0000.XXXXXXXX.app",
        "browse": "Elegir .app",
        "open_out": "Abrir carpeta de salida",
        "help_btn": "Ayuda (F1)",
        "out": "Carpeta de salida (la misma del programa):\n{p}",
        "f1": "Presiona F1 para ver cómo sacar el .app de un .CIA con GodMode9",
        "ftype": "Aplicación 3DS (*.app)",
        "all": "Todos los archivos",
        "working": "Parcheando: {n}",
        "done": "✔ Listo → {o}",
        "modes": "   Modo OLD 3DS: 0x{a:X} → 0x{b:X}   |   Modo NEW 3DS: 0x{c:X} → 0x{d:X}",
        "ctr": "   ctrtool: {l}",
        "err_small": "✘ {n}: el archivo es demasiado pequeño para ser un .app válido.",
        "err_magic": "✘ {n}: no es un .app válido (no se encontró la cabecera NCCH).",
        "err_noexh": "✘ {n}: este .app no tiene ExHeader, no se puede parchear.",
        "err_crypto": "✘ {n}: el .app sigue cifrado. Descífralo primero (mira F1).",
        "err_verify": "✘ {n}: falló la verificación del archivo parcheado.",
        "err_other": "✘ {n}: error — {e}",
        "help_title": "Cómo sacar el .app de un .CIA (GodMode9)",
        "help": (
            "CÓMO SACAR EL 0000.XXXXXXXX.app DE CUALQUIER .CIA CON GODMODE9\n"
            "══════════════════════════════════════════════════════════════\n\n"
            "1. Copia tu archivo .cia a la tarjeta SD de tu 3DS (en cualquier carpeta).\n\n"
            "2. Enciende la consola manteniendo START para abrir GodMode9.\n\n"
            "3. Entra a [0:] SDCARD, selecciona tu archivo .cia y presiona A.\n\n"
            "4. Elige \"Mount image to drive\" (opciones de imagen CIA).\n\n"
            "5. Se abre una unidad virtual (por ejemplo G:). Dentro verás varios\n"
            "   archivos: .tmd, .app, etc.\n"
            "   → El que necesitas es  0000.XXXXXXXX.app  (índice 0000, es el\n"
            "     contenido principal del juego y normalmente el más pesado).\n\n"
            "6. Resáltalo y presiona Y (copiar). Ve a  [0:] SDCARD / gm9 / out\n"
            "   (o cualquier carpeta) y presiona Y otra vez → \"Copy path here\".\n\n"
            "7. Si el .app está cifrado: resáltalo, presiona A →\n"
            "   \"NCCH image options\" → \"Decrypt file (0:/gm9/out)\".\n"
            "   Usa la copia descifrada.\n\n"
            "8. Apaga la consola, saca la SD y copia el .app a tu PC.\n\n"
            "9. Arrástralo a este programa. El archivo parcheado\n"
            "   (nombre_max.app) se crea en la misma carpeta del programa.\n\n"
            "Nota: el .app parcheado queda con la firma inválida, así que tu\n"
            "consola necesita custom firmware con las comprobaciones de firma\n"
            "desactivadas (por ejemplo Luma3DS) para ejecutarlo cuando lo vuelvas\n"
            "a meter en un CIA.\n\n"
            "Presiona F1 o Esc para cerrar esta ventana."
        ),
    },
    "pt": {
        "title": "3DS RAM Unlock Patcher",
        "lang": "Idioma",
        "drop": "Arraste aqui o seu 0000.XXXXXXXX.app\n\nou clique para escolher",
        "drop_nodnd": "Clique aqui para escolher o seu 0000.XXXXXXXX.app",
        "browse": "Escolher .app",
        "open_out": "Abrir pasta de saída",
        "help_btn": "Ajuda (F1)",
        "out": "Pasta de saída (a mesma do programa):\n{p}",
        "f1": "Pressione F1 para ver como extrair o .app de um .CIA com o GodMode9",
        "ftype": "Aplicativo 3DS (*.app)",
        "all": "Todos os arquivos",
        "working": "Aplicando patch: {n}",
        "done": "✔ Pronto → {o}",
        "modes": "   Modo OLD 3DS: 0x{a:X} → 0x{b:X}   |   Modo NEW 3DS: 0x{c:X} → 0x{d:X}",
        "ctr": "   ctrtool: {l}",
        "err_small": "✘ {n}: o arquivo é pequeno demais para ser um .app válido.",
        "err_magic": "✘ {n}: não é um .app válido (cabeçalho NCCH não encontrado).",
        "err_noexh": "✘ {n}: este .app não tem ExHeader, não dá para aplicar o patch.",
        "err_crypto": "✘ {n}: o .app ainda está criptografado. Descriptografe antes (veja F1).",
        "err_verify": "✘ {n}: a verificação do arquivo modificado falhou.",
        "err_other": "✘ {n}: erro — {e}",
        "help_title": "Como extrair o .app de um .CIA (GodMode9)",
        "help": (
            "COMO EXTRAIR O 0000.XXXXXXXX.app DE QUALQUER .CIA COM O GODMODE9\n"
            "══════════════════════════════════════════════════════════════\n\n"
            "1. Copie o seu arquivo .cia para o cartão SD do 3DS (em qualquer pasta).\n\n"
            "2. Ligue o console segurando START para abrir o GodMode9.\n\n"
            "3. Entre em [0:] SDCARD, selecione o arquivo .cia e pressione A.\n\n"
            "4. Escolha \"Mount image to drive\" (opções de imagem CIA).\n\n"
            "5. Uma unidade virtual será aberta (por exemplo G:). Dentro dela\n"
            "   haverá vários arquivos: .tmd, .app, etc.\n"
            "   → O que você precisa é  0000.XXXXXXXX.app  (índice 0000, é o\n"
            "     conteúdo principal do jogo e geralmente o maior arquivo).\n\n"
            "6. Selecione-o e pressione Y (copiar). Vá para  [0:] SDCARD / gm9 / out\n"
            "   (ou qualquer pasta) e pressione Y de novo → \"Copy path here\".\n\n"
            "7. Se o .app estiver criptografado: selecione-o, pressione A →\n"
            "   \"NCCH image options\" → \"Decrypt file (0:/gm9/out)\".\n"
            "   Use a cópia descriptografada.\n\n"
            "8. Desligue o console, retire o SD e copie o .app para o PC.\n\n"
            "9. Arraste-o para este programa. O arquivo modificado\n"
            "   (nome_max.app) é criado na mesma pasta do programa.\n\n"
            "Observação: o .app modificado fica com a assinatura inválida, então o\n"
            "console precisa de custom firmware com a verificação de assinatura\n"
            "desativada (por exemplo Luma3DS) para executá-lo depois de colocá-lo\n"
            "de volta em um CIA.\n\n"
            "Pressione F1 ou Esc para fechar esta janela."
        ),
    },
}


# --------------------------------------------------------------------------
#  Interfaz
# --------------------------------------------------------------------------
class App:
    def __init__(self):
        try:  # nitidez en pantallas con escala
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
        self.lang = "es"
        self.help_win = None
        self.help_text = None
        self.q = queue.Queue()
        self.out_dir = app_dir()

        r = self.root
        r.configure(bg=BG)
        r.geometry("720x640")
        r.minsize(620, 560)
        r.bind("<F1>", self.toggle_help)

        # --- barra superior: idioma ---
        top = tk.Frame(r, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 0))
        self.lbl_lang = tk.Label(top, bg=BG, fg=FG, font=FONT_B)
        self.lbl_lang.pack(side="left")
        self.lang_btns = {}
        for code, name in reversed(LANGS):
            b = self.button(top, name, lambda c=code: self.set_lang(c))
            b.pack(side="right", padx=(6, 0))
            self.lang_btns[code] = b

        # --- titulo ---
        self.lbl_title = tk.Label(r, bg=BG, fg=FG, font=FONT_T)
        self.lbl_title.pack(pady=(14, 8))

        # --- zona de arrastre ---
        self.zone = tk.Label(
            r, bg=BG, fg=FG, font=("Segoe UI", 13), justify="center", cursor="hand2",
            highlightthickness=2, highlightbackground=CYAN, highlightcolor=CYAN, bd=0)
        self.zone.pack(fill="x", padx=16, ipady=34)
        self.zone.bind("<Button-1>", lambda e: self.browse())
        self.zone.bind("<Enter>", lambda e: self.zone.config(bg=HOVER))
        self.zone.bind("<Leave>", lambda e: self.zone.config(bg=BG))
        if HAS_DND:
            for w in (self.zone, r):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", self.on_drop)
            self.zone.dnd_bind("<<DropEnter>>", self.drop_enter)
            self.zone.dnd_bind("<<DropLeave>>", self.drop_leave)

        # --- botones ---
        row = tk.Frame(r, bg=BG)
        row.pack(pady=12)
        self.btn_browse = self.button(row, "", self.browse)
        self.btn_browse.pack(side="left", padx=6)
        self.btn_open = self.button(row, "", self.open_out)
        self.btn_open.pack(side="left", padx=6)
        self.btn_help = self.button(row, "", self.toggle_help)
        self.btn_help.pack(side="left", padx=6)

        self.lbl_out = tk.Label(r, bg=BG, fg=MUTED, font=("Segoe UI", 9),
                                wraplength=660, justify="center")
        self.lbl_out.pack(padx=16)

        self.lbl_f1 = tk.Label(r, bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.lbl_f1.pack(side="bottom", pady=(0, 10))

        # --- registro ---
        box = tk.Frame(r, bg=BG, highlightthickness=2, highlightbackground=CYAN, bd=0)
        box.pack(fill="both", expand=True, padx=16, pady=(12, 8))
        sb = tk.Scrollbar(box, troughcolor=BG, bg=BG, bd=0, relief="flat")
        sb.pack(side="right", fill="y")
        self.log = tk.Text(box, bg=BG, fg=FG, insertbackground=FG, font=("Consolas", 10),
                           bd=0, wrap="word", state="disabled", yscrollcommand=sb.set,
                           highlightthickness=0, padx=8, pady=6)
        self.log.pack(side="left", fill="both", expand=True)
        sb.config(command=self.log.yview)
        self.log.tag_config("ok", foreground="#7CFFB2")
        self.log.tag_config("err", foreground="#FF7B7B")
        self.log.tag_config("dim", foreground=MUTED)

        self.apply_lang()
        self.root.after(100, self.poll)

    # ---- helpers de widgets ----
    def button(self, parent, text, cmd):
        b = tk.Button(parent, text=text, command=cmd, bg=BG, fg=FG, font=FONT_B,
                      activebackground=CYAN, activeforeground=BG, relief="flat", bd=0,
                      highlightthickness=2, highlightbackground=CYAN, highlightcolor=CYAN,
                      padx=14, pady=6, cursor="hand2")
        return b

    def t(self, key, **kw):
        s = T[self.lang][key]
        return s.format(**kw) if kw else s

    # ---- idioma ----
    def set_lang(self, code):
        self.lang = code
        self.apply_lang()

    def apply_lang(self):
        self.root.title(self.t("title"))
        self.lbl_lang.config(text=self.t("lang") + ":")
        self.lbl_title.config(text=self.t("title"))
        self.zone.config(text=self.t("drop") if HAS_DND else self.t("drop_nodnd"))
        self.btn_browse.config(text=self.t("browse"))
        self.btn_open.config(text=self.t("open_out"))
        self.btn_help.config(text=self.t("help_btn"))
        self.lbl_out.config(text=self.t("out", p=self.out_dir))
        self.lbl_f1.config(text=self.t("f1"))
        for code, b in self.lang_btns.items():
            if code == self.lang:
                b.config(bg=CYAN, fg=BG)
            else:
                b.config(bg=BG, fg=FG)
        if self.help_win is not None:
            self.help_win.title(self.t("help_title"))
            self.fill_help()

    # ---- ayuda (F1) ----
    def toggle_help(self, event=None):
        if self.help_win is not None:
            self.close_help()
            return "break"
        w = tk.Toplevel(self.root)
        self.help_win = w
        w.configure(bg=BG)
        w.title(self.t("help_title"))
        w.geometry("700x600")
        w.transient(self.root)
        box = tk.Frame(w, bg=BG, highlightthickness=2, highlightbackground=CYAN)
        box.pack(fill="both", expand=True, padx=14, pady=14)
        sb = tk.Scrollbar(box, troughcolor=BG, bg=BG, bd=0, relief="flat")
        sb.pack(side="right", fill="y")
        self.help_text = tk.Text(box, bg=BG, fg=FG, font=("Consolas", 10), bd=0, wrap="word",
                                 highlightthickness=0, padx=12, pady=10, yscrollcommand=sb.set)
        self.help_text.pack(side="left", fill="both", expand=True)
        sb.config(command=self.help_text.yview)
        self.fill_help()
        w.bind("<F1>", self.toggle_help)
        w.bind("<Escape>", lambda e: self.close_help())
        w.protocol("WM_DELETE_WINDOW", self.close_help)
        w.focus_set()
        return "break"

    def fill_help(self):
        self.help_text.config(state="normal")
        self.help_text.delete("1.0", "end")
        self.help_text.insert("1.0", self.t("help"))
        self.help_text.config(state="disabled")

    def close_help(self):
        if self.help_win is not None:
            self.help_win.destroy()
        self.help_win = None
        self.help_text = None

    # ---- archivos ----
    def drop_enter(self, event):
        self.zone.config(bg=HOVER)
        return event.action

    def drop_leave(self, event):
        self.zone.config(bg=BG)
        return event.action

    def on_drop(self, event):
        self.zone.config(bg=BG)
        self.start(list(self.root.tk.splitlist(event.data)))
        return event.action

    def browse(self):
        paths = filedialog.askopenfilenames(
            title=self.t("browse"),
            filetypes=[(self.t("ftype"), "*.app"), (self.t("all"), "*.*")])
        if paths:
            self.start(list(paths))

    def open_out(self):
        try:
            if os.name == "nt":
                os.startfile(self.out_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.out_dir])
            else:
                subprocess.Popen(["xdg-open", self.out_dir])
        except Exception:
            pass

    # ---- trabajo en segundo plano ----
    def start(self, paths):
        files = [p for p in paths if os.path.isfile(p)]
        if files:
            threading.Thread(target=self.worker, args=(files,), daemon=True).start()

    def worker(self, files):
        for p in files:
            n = os.path.basename(p)
            self.q.put(("dim", self.t("working", n=n)))
            try:
                res = patch_app(p, self.out_dir)
                self.q.put(("ok", self.t("done", o=res["out"])))
                (a, c), (b, d) = res["before"], res["after"]
                self.q.put(("dim", self.t("modes", a=a, b=b, c=c, d=d)))
                for line in ctrtool_check(res["out"]):
                    self.q.put(("dim", self.t("ctr", l=line)))
            except PatchError as e:
                self.q.put(("err", self.t(e.key, n=n)))
            except Exception as e:  # noqa
                self.q.put(("err", self.t("err_other", n=n, e=e)))

    def poll(self):
        try:
            while True:
                tag, text = self.q.get_nowait()
                self.log.config(state="normal")
                self.log.insert("end", text + "\n", tag)
                self.log.see("end")
                self.log.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
