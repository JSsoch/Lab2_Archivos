import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from contact_manager import ContactManager, RECORD_SIZE


class AgendaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Agenda de Contactos - Acceso Aleatorio e Índice Primario")
        self.geometry("880x560")

        self.manager = ContactManager()

        self.style = ttk.Style(self)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        self.build_menu()
        self.setup_ui()
        self.refresh_table()

    def build_menu(self):
        menubar = tk.Menu(self, font=("Segoe UI", 10))

        # 1. Menú Contactos (Funcional: Agregar, Buscar por ID y Modificar)
        contactos_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        contactos_menu.add_command(label="Agregar contacto", command=self.focus_add_form)
        contactos_menu.add_command(label="Buscar por ID", command=self.prompt_search_by_id)
        contactos_menu.add_command(label="Modificar contacto", command=self.update_existing_contact)
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

        # Panel izquierdo: Búsqueda por índice y Formulario de Contacto
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="y", padx=(0, 15))

        # Barra de búsqueda rápida por ID mediante indice.json
        search_frame = ttk.LabelFrame(left_panel, text=" Búsqueda Directa por ID (Índice JSON) ", padding=10)
        search_frame.pack(fill="x", pady=(0, 10))

        self.search_id_entry = ttk.Entry(search_frame, width=16, font=("Segoe UI", 10))
        self.search_id_entry.pack(side="left", padx=(0, 6))
        self.search_id_entry.bind("<Return>", lambda e: self.search_contact_from_bar())

        btn_search = ttk.Button(search_frame, text="Buscar ID", command=self.search_contact_from_bar)
        btn_search.pack(side="left")

        # Formulario de Contacto
        form_frame = ttk.LabelFrame(left_panel, text=" Datos del Contacto (120 bytes fijos) ", padding=12)
        form_frame.pack(fill="both", expand=True)

        labels = [
            ("ID (Entero único):", "id"),
            ("Nombre (máx 30):", "nombre"),
            ("Teléfono (máx 15):", "telefono"),
            ("Correo (máx 40):", "correo"),
            ("Ciudad (máx 28):", "ciudad")
        ]

        self.entries = {}
        for row, (text, key) in enumerate(labels):
            ttk.Label(form_frame, text=text, font=("Segoe UI", 9)).grid(row=row * 2, column=0, sticky="w", pady=(4, 0))
            entry = ttk.Entry(form_frame, width=28, font=("Segoe UI", 10))
            entry.grid(row=row * 2 + 1, column=0, sticky="we", pady=(2, 5))
            self.entries[key] = entry

        btn_save = ttk.Button(form_frame, text="Agregar Nuevo Contacto", command=self.save_contact)
        btn_save.grid(row=len(labels) * 2, column=0, sticky="we", pady=(10, 4))

        btn_update = ttk.Button(form_frame, text="Modificar Contacto (In-Place)", command=self.update_existing_contact)
        btn_update.grid(row=len(labels) * 2 + 1, column=0, sticky="we", pady=(0, 4))

        btn_clear = ttk.Button(form_frame, text="Limpiar Formulario", command=self.clear_form)
        btn_clear.grid(row=len(labels) * 2 + 2, column=0, sticky="we")

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
        self.tree.column("offset", width=85, anchor="center")
        self.tree.column("id", width=55, anchor="center")
        self.tree.column("nombre", width=135)
        self.tree.column("telefono", width=90)
        self.tree.column("correo", width=145)
        self.tree.column("ciudad", width=95)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Barra de estado inferior mostrando información de seek() y tell()
        self.status_bar = ttk.Label(
            self,
            text=f" Archivo: contactos.dat  |  Índice: indice.json ({len(self.manager.index)} entradas)  |  Tamaño fijo: {RECORD_SIZE} bytes",
            relief="sunken",
            anchor="w",
            padding=4
        )
        self.status_bar.pack(side="bottom", fill="x")

    def focus_add_form(self):
        self.clear_form()
        self.entries["id"].focus_set()

    def clear_form(self):
        self.entries["id"].configure(state="normal")
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def fill_form(self, contact):
        self.entries["id"].configure(state="normal")
        self.entries["id"].delete(0, tk.END)
        self.entries["id"].insert(0, str(contact["id"]))

        self.entries["nombre"].delete(0, tk.END)
        self.entries["nombre"].insert(0, contact["nombre"])

        self.entries["telefono"].delete(0, tk.END)
        self.entries["telefono"].insert(0, contact["telefono"])

        self.entries["correo"].delete(0, tk.END)
        self.entries["correo"].insert(0, contact["correo"])

        self.entries["ciudad"].delete(0, tk.END)
        self.entries["ciudad"].insert(0, contact["ciudad"])

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], "values")
        if values:
            contact_id = values[2]
            contact = self.manager.search_by_id(contact_id)
            if contact:
                self.fill_form(contact)
                self.status_bar.configure(
                    text=(
                        f" Acceso directo [seek({contact['offset']})] -> Registro #{contact['registro']}  |  "
                        f"tell() inicio: {contact['offset']} bytes  |  tell() fin lectura: {contact['tell_after_read']} bytes"
                    )
                )

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

        try:
            rec_num, offset = self.manager.add_contact(int(c_id), nombre, telefono, correo, ciudad)
            self.status_bar.configure(
                text=(
                    f" Contacto ID {c_id} agregado en Registro #{rec_num}  |  "
                    f"Posición tell(): {offset} bytes  |  Índice actualizado en indice.json"
                )
            )
            self.clear_form()
            self.refresh_table()
        except ValueError as e:
            messagebox.showerror("ID Duplicado", str(e))

    def search_contact_from_bar(self):
        c_id = self.search_id_entry.get().strip()
        if not c_id:
            messagebox.showwarning("Búsqueda", "Ingrese un ID numérico para buscar.")
            return
        self.execute_search(c_id)

    def prompt_search_by_id(self):
        c_id = simpledialog.askstring("Buscar por ID", "Ingrese el ID del contacto a buscar en el índice:", parent=self)
        if c_id is not None and c_id.strip():
            self.search_id_entry.delete(0, tk.END)
            self.search_id_entry.insert(0, c_id.strip())
            self.execute_search(c_id.strip())

    def execute_search(self, c_id):
        if not c_id.isdigit():
            messagebox.showwarning("Validación", "El ID a buscar debe ser un número entero.")
            return

        contact = self.manager.search_by_id(int(c_id))
        if not contact:
            self.status_bar.configure(text=f" Búsqueda en indice.json: El ID {c_id} no existe en la agenda.")
            messagebox.showinfo("No encontrado", f"No existe ningún contacto registrado con el ID {c_id}.")
            return

        self.fill_form(contact)
        # Resaltar fila en el Treeview
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if str(vals[2]) == str(contact["id"]):
                self.tree.selection_set(item)
                self.tree.see(item)
                break

        self.status_bar.configure(
            text=(
                f" ID {c_id} encontrado en indice.json -> Registro #{contact['registro']}  |  "
                f"seek({contact['offset']})  |  tell() antes: {contact['offset']}B, después: {contact['tell_after_read']}B"
            )
        )
        messagebox.showinfo(
            "Contacto Encontrado (Acceso Aleatorio)",
            f"ID: {contact['id']}\n"
            f"Nombre: {contact['nombre']}\n"
            f"Teléfono: {contact['telefono']}\n"
            f"Correo: {contact['correo']}\n"
            f"Ciudad: {contact['ciudad']}\n\n"
            f"• Registro en índice: #{contact['registro']}\n"
            f"• Posición seek()/tell(): byte {contact['offset']} al {contact['tell_after_read']}"
        )

    def update_existing_contact(self):
        c_id = self.entries["id"].get().strip()
        nombre = self.entries["nombre"].get().strip()
        telefono = self.entries["telefono"].get().strip()
        correo = self.entries["correo"].get().strip()
        ciudad = self.entries["ciudad"].get().strip()

        if not c_id.isdigit():
            messagebox.showwarning(
                "Modificar Contacto",
                "Seleccione o busque primero un contacto válido por su ID para modificarlo."
            )
            return

        if not nombre:
            messagebox.showwarning("Validación", "El campo Nombre no puede quedar vacío.")
            return

        try:
            rec_num, start_pos, end_pos = self.manager.update_contact(int(c_id), nombre, telefono, correo, ciudad)
            self.status_bar.configure(
                text=(
                    f" Modificación In-Place exitosa: ID {c_id} en Registro #{rec_num}  |  "
                    f"seek({start_pos}) -> sobrescritos {end_pos - start_pos} bytes (tell final: {end_pos})"
                )
            )
            self.refresh_table()
            messagebox.showinfo(
                "Modificación en el lugar",
                f"Contacto ID {c_id} actualizado directamente en el Registro #{rec_num}.\n\n"
                f"• Offset inicial (tell): {start_pos} bytes\n"
                f"• Offset final (tell): {end_pos} bytes\n"
                f"• Solo se sobrescribieron los {RECORD_SIZE} bytes de este registro."
            )
        except KeyError as e:
            messagebox.showerror("ID no encontrado", str(e))

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
            "Agenda de Contactos con Acceso Aleatorio v0.2\n\n"
            f"• Tamaño fijo por registro: {RECORD_SIZE} bytes.\n"
            "• Índice primario almacenado en 'indice.json'.\n"
            "• Búsqueda por ID y modificación in-place mediante seek() y tell()."
        )


if __name__ == "__main__":
    app = AgendaApp()
    app.mainloop()
