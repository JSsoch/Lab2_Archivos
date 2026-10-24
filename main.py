import tkinter as tk
from tkinter import ttk, messagebox
from contact_manager import ContactManager, RECORD_SIZE


class AgendaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Agenda de Contactos - Acceso Aleatorio (Avance Inicial)")
        self.geometry("820x520")

        self.manager = ContactManager()

        self.style = ttk.Style(self)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.build_menu()
        self.setup_ui()
        self.refresh_table()

    def build_menu(self):
        menubar = tk.Menu(self, font=("Segoe UI", 10))

        # 1. Menú Contactos
        contactos_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        contactos_menu.add_command(label="Agregar contacto", command=self.focus_add_form)
        contactos_menu.add_command(label="Buscar por ID", command=lambda: self.pending_feature("Buscar por ID con índice"))
        contactos_menu.add_command(label="Modificar contacto", command=lambda: self.pending_feature("Modificar en el lugar (in-place)"))
        contactos_menu.add_separator()
        contactos_menu.add_command(label="Salir", command=self.quit)
        menubar.add_cascade(label="Contactos", menu=contactos_menu)

        # 2. Menú Exportar
        exportar_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        exportar_menu.add_command(label="Exportar a JSON", command=lambda: self.pending_feature("Exportar a JSON"))
        exportar_menu.add_command(label="Generar reporte PDF", command=lambda: self.pending_feature("Generar reporte PDF"))
        menubar.add_cascade(label="Exportar", menu=exportar_menu)

        # 3. Menú Herramientas
        herramientas_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        herramientas_menu.add_command(label="Verificar integridad (SHA-256)", command=lambda: self.pending_feature("Verificar integridad SHA-256"))
        herramientas_menu.add_command(label="Crear respaldo ZIP", command=lambda: self.pending_feature("Crear respaldo ZIP"))
        herramientas_menu.add_command(label="Información del archivo", command=lambda: self.pending_feature("Información y permisos del archivo"))
        menubar.add_cascade(label="Herramientas", menu=herramientas_menu)

        # 4. Menú Ayuda (simulado)
        ayuda_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        ayuda_menu.add_command(label="Acerca de...", command=self.show_help)
        menubar.add_cascade(label="Ayuda", menu=ayuda_menu)

        self.config(menu=menubar)

    def setup_ui(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Panel izquierdo: Formulario básico de registro
        form_frame = ttk.LabelFrame(main_frame, text=" Registro de Contacto (Tamaño Fijo) ", padding=15)
        form_frame.pack(side="left", fill="y", padx=(0, 15))

        labels = [
            ("ID (Entero único):", "id"),
            ("Nombre (máx 30):", "nombre"),
            ("Teléfono (máx 15):", "telefono"),
            ("Correo (máx 40):", "correo"),
            ("Ciudad (máx 28):", "ciudad")
        ]

        self.entries = {}
        for row, (text, key) in enumerate(labels):
            ttk.Label(form_frame, text=text, font=("Segoe UI", 9)).grid(row=row * 2, column=0, sticky="w", pady=(5, 0))
            entry = ttk.Entry(form_frame, width=28, font=("Segoe UI", 10))
            entry.grid(row=row * 2 + 1, column=0, sticky="we", pady=(2, 6))
            self.entries[key] = entry

        btn_save = ttk.Button(form_frame, text="Guardar Registro", command=self.save_contact)
        btn_save.grid(row=len(labels) * 2, column=0, sticky="we", pady=(12, 4))

        btn_clear = ttk.Button(form_frame, text="Limpiar Campos", command=self.clear_form)
        btn_clear.grid(row=len(labels) * 2 + 1, column=0, sticky="we")

        # Panel derecho: Tabla de visualización y lectura directa
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True)

        columns = ("reg", "offset", "id", "nombre", "telefono", "correo", "ciudad")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=16)

        self.tree.heading("reg", text="# Reg")
        self.tree.heading("offset", text="Offset (tell)")
        self.tree.heading("id", text="ID")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("telefono", text="Teléfono")
        self.tree.heading("correo", text="Correo")
        self.tree.heading("ciudad", text="Ciudad")

        self.tree.column("reg", width=50, anchor="center")
        self.tree.column("offset", width=80, anchor="center")
        self.tree.column("id", width=55, anchor="center")
        self.tree.column("nombre", width=130)
        self.tree.column("telefono", width=90)
        self.tree.column("correo", width=140)
        self.tree.column("ciudad", width=95)

        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Barra de estado inferior mostrando información de seek() y tell()
        self.status_bar = ttk.Label(
            self,
            text=f" Archivo: contactos.dat  |  Tamaño de registro fijo: {RECORD_SIZE} bytes  |  Listo",
            relief="sunken",
            anchor="w",
            padding=4
        )
        self.status_bar.pack(side="bottom", fill="x")

    def focus_add_form(self):
        self.clear_form()
        self.entries["id"].focus_set()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)

    def save_contact(self):
        c_id = self.entries["id"].get().strip()
        nombre = self.entries["nombre"].get().strip()
        telefono = self.entries["telefono"].get().strip()
        correo = self.entries["correo"].get().strip()
        ciudad = self.entries["ciudad"].get().strip()

        if not c_id.isdigit():
            messagebox.showwarning("Validación", "El ID debe ser un número entero.")
            return

        if not nombre:
            messagebox.showwarning("Validación", "El campo Nombre es obligatorio.")
            return

        rec_num, offset = self.manager.add_contact(int(c_id), nombre, telefono, correo, ciudad)
        self.status_bar.configure(
            text=f" Contacto agregado en Registro #{rec_num}  |  Posición tell(): {offset} bytes  |  Tamaño fijo: {RECORD_SIZE} bytes"
        )
        self.clear_form()
        self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        contacts = self.manager.get_all_contacts()
        for c in contacts:
            self.tree.insert(
                "",
                tk.END,
                values=(c["registro"], c["offset"], c["id"], c["nombre"], c["telefono"], c["correo"], c["ciudad"])
            )

    def pending_feature(self, feature_name):
        self.status_bar.configure(text=f" Acción seleccionada: {feature_name} (En desarrollo para próximos commits)")
        messagebox.showinfo("En desarrollo", f"La función '{feature_name}' se implementará en el siguiente commit.")

    def show_help(self):
        messagebox.showinfo(
            "Ayuda (Simulado)",
            "Agenda de Contactos con Acceso Aleatorio v0.1\n\n"
            f"Cada registro ocupa exactamente {RECORD_SIZE} caracteres rellenados con espacios (ljust)."
        )


if __name__ == "__main__":
    app = AgendaApp()
    app.mainloop()
