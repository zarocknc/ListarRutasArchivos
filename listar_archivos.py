import os
import json
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

HISTORIAL_FILE = "historial_rutas.txt"

root = tk.Tk()
root.title("Gestor de Rutas")
root.geometry("700x500")


def centrar_ventana(ventana, width=600, height=400):
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (width // 2)
    y = (ventana.winfo_screenheight() // 2) - (height // 2)
    ventana.geometry(f"{width}x{height}+{x}+{y}")


centrar_ventana(root)

historial = []


def leer_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, "r") as f:
            return [line.strip() for line in f.readlines()]
    return []


def escribir_historial():
    with open(HISTORIAL_FILE, "w") as f:
        for ruta in historial:
            f.write(ruta + "\n")


def obtener_archivos(ruta):
    archivos = []
    carpetas_omitidas = {"node_modules", ".git", "build", "dist", "venv"}
    try:
        for dirpath, dirnames, filenames in os.walk(ruta):
            for carpeta in carpetas_omitidas:
                if carpeta in dirnames:
                    archivos.append(os.path.join(dirpath, carpeta))
                    dirnames.remove(carpeta)
            for filename in filenames:
                archivos.append(os.path.join(dirpath, filename))
    except Exception as e:
        print(f"Error al acceder al directorio: {e}")
    mostrar_archivos(archivos)


def mostrar_archivos(archivos):
    archivos_listbox.delete(0, tk.END)
    for archivo in archivos:
        archivos_listbox.insert(tk.END, archivo)


def seleccionar_carpeta_y_buscar():
    carpeta = filedialog.askdirectory(title="Seleccionar Carpeta")
    if carpeta:
        obtener_archivos(carpeta)
        if carpeta not in historial:
            historial.append(carpeta)
            historial_listbox.insert(tk.END, carpeta)
            escribir_historial()
        ventana.destroy()


def ventana_buscar_ruta():
    global ventana
    ventana = tk.Toplevel(root)
    ventana.title("Buscar o Seleccionar Carpeta")
    ventana.geometry("400x180")
    centrar_ventana(ventana, 400, 180)

    label = tk.Label(ventana, text="Pega la ruta o selecciona una carpeta:")
    label.pack(pady=10)

    ruta_entry = tk.Entry(ventana, width=50)
    ruta_entry.insert(0, "Pega la ruta aquí ")
    ruta_entry.bind("<FocusIn>", lambda event: ruta_entry.delete(0, tk.END))
    ruta_entry.pack(pady=5)

    frame_botones_ventana = tk.Frame(ventana)
    frame_botones_ventana.pack(pady=10)

    buscar_carpeta_button = tk.Button(
        frame_botones_ventana,
        text="Seleccionar Carpeta",
        command=seleccionar_carpeta_y_buscar,
    )
    buscar_carpeta_button.pack(side=tk.LEFT, padx=5)

    def confirmar_ruta():
        ruta = ruta_entry.get()
        if ruta and ruta != "Escribe la ruta aquí":
            obtener_archivos(ruta)
            if ruta not in historial:
                historial.append(ruta)
                historial_listbox.insert(tk.END, ruta)
                escribir_historial()
        ventana.destroy()

    confirmar_button = tk.Button(
        frame_botones_ventana, text="Buscar ruta", command=confirmar_ruta
    )
    confirmar_button.pack(side=tk.LEFT, padx=5)


def copiar_rutas():
    rutas = archivos_listbox.get(0, tk.END)
    if rutas:
        root.clipboard_clear()
        root.clipboard_append("\n".join(rutas))
        mostrar_notificacion("Rutas copiadas al portapapeles")
    else:
        messagebox.showwarning(
            "Advertencia", "Debe ingresar la ruta para realizar la búsqueda."
        )


def mostrar_notificacion(mensaje):
    notificacion_label.config(text=mensaje)
    notificacion_label.pack()
    root.after(2000, ocultar_notificacion)


def ocultar_notificacion():
    notificacion_label.pack_forget()


def seleccionar_historial(event):
    seleccion = historial_listbox.curselection()
    if seleccion:
        ruta = historial_listbox.get(seleccion)
        obtener_archivos(ruta)


def generar_prompt():
    rutas = archivos_listbox.get(0, tk.END)
    if not rutas:
        messagebox.showwarning(
            "Advertencia", "Debe ingresar la ruta para generar el prompt."
        )
        return

    carpeta_principal = os.path.basename(os.path.dirname(rutas[0]))
    encabezado = (
        "Hola, a continuación te muestro un resumen detallado del proyecto. "
        "Úsalo para entender su estructura y responder a mis preguntas sobre su organización y configuración. "
        "Aquí está la estructura general del proyecto:"
    )
    contenido_prompt = (
        f"{encabezado}\n\n## Estructura General del Proyecto:\n\n"
        + "\n".join(rutas)
        + "\n\n"
    )

    archivos_clave = [
        "package.json",
        "Dockerfile",
        "docker-compose.yml",
        ".env",
        "tsconfig.json",
    ]
    dependencias_clave = []
    rutas_api = []
    scripts_importantes = []

    for ruta in rutas:
        for archivo in archivos_clave:
            if ruta.endswith(archivo):
                try:
                    with open(ruta, "r") as file:
                        contenido = file.read()
                        nombre_servicio = os.path.basename(os.path.dirname(ruta))
                        contexto = f"{archivo} en el servicio '{nombre_servicio}'"
                        contenido_prompt += f"### Contenido de {contexto}:\n{ruta}\n\n```\n{contenido}\n```\n\n"

                        if archivo == "package.json":
                            paquete_json = json.loads(contenido)
                            dependencias = paquete_json.get("dependencies", {})
                            dev_dependencias = paquete_json.get("devDependencies", {})
                            dependencias_clave.extend(dependencias.keys())
                            dependencias_clave.extend(dev_dependencias.keys())
                            scripts = paquete_json.get("scripts", {})
                            scripts_importantes = {
                                k: v
                                for k, v in scripts.items()
                                if k in ["start", "build", "test"]
                            }

                        if archivo.endswith((".ts", ".js")) and (
                            "route" in archivo or "controller" in archivo
                        ):
                            rutas_encontradas = re.findall(
                                r"(GET|POST|PUT|DELETE)\s+['\"](.+?)['\"]", contenido
                            )
                            for metodo, ruta in rutas_encontradas:
                                rutas_api.append(f"{metodo} {ruta}")

                except Exception as e:
                    print(f"No se pudo leer {archivo}: {e}")

    if dependencias_clave:
        contenido_prompt += (
            "\n## Dependencias Clave del Proyecto:\n"
            + ", ".join(set(dependencias_clave))
            + "\n\n"
        )

    if scripts_importantes:
        contenido_prompt += "## Scripts Clave en package.json:\n"
        for nombre, comando in scripts_importantes.items():
            contenido_prompt += f"- **{nombre}**: `{comando}`\n"
        contenido_prompt += "\n"

    if rutas_api:
        contenido_prompt += "## Resumen de Rutas de la API:\n"
        for ruta in rutas_api:
            contenido_prompt += f"- {ruta}\n"
        contenido_prompt += "\n"

    root.clipboard_clear()
    root.clipboard_append(contenido_prompt)
    mostrar_notificacion("Prompt generado y copiado al portapapeles")

    nombre_archivo = os.path.join(
        os.path.expanduser("~"), "Downloads", f"{carpeta_principal}_prompt.txt"
    )
    os.makedirs(os.path.dirname(nombre_archivo), exist_ok=True)
    with open(nombre_archivo, "w") as file:
        file.write(contenido_prompt)
    mostrar_notificacion(f"Prompt guardado como {nombre_archivo}")


frame_botones = tk.Frame(root)
frame_botones.pack(pady=10)

buscar_button = tk.Button(
    frame_botones, text="Buscar Rutas", command=ventana_buscar_ruta
)
buscar_button.pack(side=tk.LEFT, padx=5)

copiar_button = tk.Button(frame_botones, text="Copiar Rutas", command=copiar_rutas)
copiar_button.pack(side=tk.LEFT, padx=5)

generar_prompt_button = tk.Button(
    frame_botones, text="Generar Prompt", command=generar_prompt
)
generar_prompt_button.pack(side=tk.LEFT, padx=5)

archivos_listbox = tk.Listbox(root, width=80, height=10)
archivos_listbox.pack(pady=10)

historial_label = ttk.Label(root, text="Historial de Rutas Buscadas")
historial_label.pack()

frame_historial = tk.Frame(root)
frame_historial.pack(pady=5)

scrollbar_historial = tk.Scrollbar(frame_historial)
scrollbar_historial.pack(side=tk.RIGHT, fill=tk.Y)

historial_listbox = tk.Listbox(
    frame_historial, width=80, height=7, yscrollcommand=scrollbar_historial.set
)
historial_listbox.pack(side=tk.LEFT, fill=tk.BOTH)

scrollbar_historial.config(command=historial_listbox.yview)
historial_listbox.bind("<Double-1>", seleccionar_historial)

notificacion_label = tk.Label(root, text="", fg="green")

historial = leer_historial()
for ruta in historial:
    historial_listbox.insert(tk.END, ruta)

root.mainloop()
