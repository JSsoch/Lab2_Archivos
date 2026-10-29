import hashlib
import json
import os
import zipfile
from datetime import datetime
from fpdf import FPDF

CONTACTS_FILE = "contactos.dat"
INDEX_FILE = "indice.json"
HASH_FILE = "contactos.sha256"
EXPORT_JSON_FILE = "contactos_exportados.json"
REPORT_PDF_FILE = "reporte_contactos.pdf"
BACKUP_ZIP_FILE = "respaldo_agenda.zip"

# Definición de longitudes fijas para cada campo (Total = 120 caracteres / bytes en ASCII/UTF-8 base por registro)
# id: 6 | nombre: 30 | telefono: 15 | correo: 40 | ciudad: 28 | salto de línea (\n): 1 -> 120 caracteres
FIELD_LENGTHS = {
    "id": 6,
    "nombre": 30,
    "telefono": 15,
    "correo": 40,
    "ciudad": 28
}

RECORD_SIZE = sum(FIELD_LENGTHS.values()) + 1  # 119 caracteres de datos + 1 salto de línea = 120


class ContactReportPDF(FPDF):
    """
    Plantilla de reporte PDF generada con fpdf2 a partir del archivo JSON exportado.
    """

    def header(self):
        self.set_font("Helvetica", "B", 15)
        self.set_text_color(216, 67, 21)
        self.cell(0, 10, "Agenda de Contactos - Reporte Oficial", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(90, 60, 45)
        self.cell(
            0,
            6,
            f"Estudiante: Josue Soch (Carnet: 1537924)  |  Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  Registro fijo: {RECORD_SIZE} B",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C"
        )
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 90, 70)
        self.cell(0, 10, f"Pagina {self.page_no()}/{{nb}} - Generado a partir de JSON exportado (Carnet: 1537924)", align="C")


class ContactManager:
    """
    Gestor de archivos para la agenda de contactos con registros de tamaño fijo.
    Implementa:
    - Registros de longitud fija (120 bytes) rellenados con ljust() en UTF-8
    - Acceso aleatorio directo y modificación in-place mediante seek() y tell()
    - Índice primario persistente en JSON (indice.json)
    - Exportación a JSON y generación de reporte PDF con fpdf2
    - Verificación de integridad con hash SHA-256 (hashlib)
    - Respaldo comprimido en ZIP (zipfile) comparando tamaño original vs comprimido
    - Consulta de metadatos y permisos de sistema de archivos (os.stat y os.access)
    - Manejo robusto de excepciones (archivos inexistentes, corruptos o sin permisos)
    """

    def __init__(self, filename=CONTACTS_FILE, index_filename=INDEX_FILE, hash_filename=HASH_FILE):
        self.filename = filename
        self.index_filename = index_filename
        self.hash_filename = hash_filename
        self.index = {}
        self.last_error = None
        self._ensure_file_exists()
        self.load_index()

    def _ensure_file_exists(self):
        if not os.path.exists(self.filename):
            try:
                with open(self.filename, "w", encoding="utf-8", newline="\n") as f:
                    pass
                self.save_hash()
                print(f"INFO: Archivo '{self.filename}' y su hash inicial creados exitosamente.")
            except PermissionError:
                self.last_error = f"Sin permisos de escritura para crear '{self.filename}'."
                print(f"ERROR: {self.last_error}")
            except OSError as e:
                self.last_error = f"Error de sistema al crear '{self.filename}': {e}"
                print(f"ERROR: {self.last_error}")

    def calculate_sha256(self):
        """
        Calcula y retorna el hash SHA-256 actual del archivo de contactos (contactos.dat)
        utilizando el módulo hashlib.
        """
        if not os.path.exists(self.filename):
            return ""

        try:
            sha256 = hashlib.sha256()
            with open(self.filename, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except PermissionError:
            self.last_error = f"Sin permisos de lectura sobre '{self.filename}' para calcular SHA-256."
            print(f"ERROR: {self.last_error}")
            return ""
        except OSError as e:
            self.last_error = f"Fallo al calcular SHA-256: {e}"
            print(f"ERROR: {self.last_error}")
            return ""

    def save_hash(self):
        """
        Calcula el hash SHA-256 de contactos.dat y lo guarda en contactos.sha256 (UTF-8).
        Se invoca automáticamente cada vez que se guarda o modifica un contacto.
        """
        current_hash = self.calculate_sha256()
        if not current_hash:
            return ""
        try:
            with open(self.hash_filename, "w", encoding="utf-8") as f:
                f.write(current_hash + "\n")
            print(f"INFO: Hash SHA-256 actualizado en '{self.hash_filename}': {current_hash[:16]}...")
            return current_hash
        except PermissionError:
            self.last_error = f"Sin permisos de escritura en '{self.hash_filename}'."
            print(f"ERROR: {self.last_error}")
            return current_hash
        except OSError as e:
            self.last_error = f"Error al guardar hash SHA-256: {e}"
            print(f"ERROR: {self.last_error}")
            return current_hash

    def verify_integrity(self):
        """
        Recalcula el hash SHA-256 del archivo de contactos y lo compara con el almacenado
        en contactos.sha256.
        Retorna una tupla: (es_integro: bool, hash_actual: str, hash_guardado: str, mensaje: str)
        """
        if not os.path.exists(self.filename):
            return False, "", "", f"El archivo '{self.filename}' no existe."

        if not os.access(self.filename, os.R_OK):
            return False, "", "", f"No hay permisos de lectura sobre '{self.filename}'."

        current_hash = self.calculate_sha256()

        if not os.path.exists(self.hash_filename):
            if os.path.getsize(self.filename) == 0:
                self.save_hash()
                return True, current_hash, current_hash, "Archivo nuevo verificado correctamente."
            return (
                False,
                current_hash,
                "(No encontrado)",
                f"No se encontró el archivo de control '{self.hash_filename}'. El archivo pudo haber sido manipulado."
            )

        try:
            with open(self.hash_filename, "r", encoding="utf-8") as f:
                content = f.read().strip()
                stored_hash = content.split()[0] if content else ""
        except PermissionError:
            return False, current_hash, "(Sin permisos)", f"Sin permisos para leer '{self.hash_filename}'."
        except OSError as e:
            return False, current_hash, "(Error)", f"Error leyendo '{self.hash_filename}': {e}"

        if current_hash == stored_hash:
            return (
                True,
                current_hash,
                stored_hash,
                "Integridad verificada: el archivo coincide exactamente con el hash SHA-256 registrado."
            )
        else:
            return (
                False,
                current_hash,
                stored_hash,
                "¡ALERTA DE INTEGRIDAD! El archivo de contactos fue modificado fuera de la aplicación (el hash SHA-256 no coincide)."
            )

    def load_index(self):
        """
        Carga el índice primario desde indice.json.
        Si el archivo no existe o está corrupto, reconstruye el índice sin que la aplicación se caiga.
        """
        if not os.path.exists(self.index_filename):
            print(f"INFO: Archivo de índice '{self.index_filename}' no encontrado. Reconstruyendo automáticamente...")
            self.index = {}
            self.rebuild_index()
            return

        try:
            with open(self.index_filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("El contenido del índice JSON no es un objeto clave-valor.")
                self.index = {str(k): int(v) for k, v in data.items()}
            print(f"INFO: Índice cargado desde '{self.index_filename}' ({len(self.index)} registros).")
        except (json.JSONDecodeError, ValueError) as e:
            self.last_error = f"Índice '{self.index_filename}' corrupto ({e}). Reconstruido automáticamente."
            print(f"ERROR: {self.last_error}")
            self.rebuild_index()
        except PermissionError:
            self.last_error = f"Sin permisos de lectura para '{self.index_filename}'. Usando índice en memoria."
            print(f"ERROR: {self.last_error}")
            self.index = {}
        except OSError as e:
            self.last_error = f"Fallo al abrir '{self.index_filename}': {e}"
            print(f"ERROR: {self.last_error}")
            self.index = {}

    def save_index(self):
        """
        Guarda el diccionario de índice primario {id: numero_de_registro} en indice.json (UTF-8).
        """
        try:
            with open(self.index_filename, "w", encoding="utf-8") as f:
                json.dump(self.index, f, indent=4, ensure_ascii=False)
            return True
        except PermissionError:
            self.last_error = f"Sin permisos de escritura para guardar el índice '{self.index_filename}'."
            print(f"ERROR: {self.last_error}")
            return False
        except OSError as e:
            self.last_error = f"Error al escribir '{self.index_filename}': {e}"
            print(f"ERROR: {self.last_error}")
            return False

    def rebuild_index(self):
        """
        Recorre los registros de tamaño fijo para reconstruir el índice primario si no existe o se corrompió.
        """
        self.index = {}
        if not os.path.exists(self.filename):
            self.save_index()
            return

        try:
            with open(self.filename, "r", encoding="utf-8", newline="\n") as f:
                record_num = 0
                while True:
                    f.seek(record_num * RECORD_SIZE)
                    raw_data = f.read(RECORD_SIZE)
                    if not raw_data or len(raw_data) < RECORD_SIZE - 1:
                        break
                    parsed = self.parse_record(raw_data)
                    if parsed and str(parsed["id"]).strip() != "":
                        self.index[str(parsed["id"])] = record_num
                    record_num += 1
            self.save_index()
        except PermissionError:
            self.last_error = f"Sin permisos para leer '{self.filename}' durante la reconstrucción del índice."
            print(f"ERROR: {self.last_error}")
        except OSError as e:
            self.last_error = f"Error reconstruyendo el índice: {e}"
            print(f"ERROR: {self.last_error}")

    @staticmethod
    def _normalize_fixed_ascii(text, max_len):
        """
        Ajusta la cadena a longitud fija exacta en caracteres y bytes UTF-8 usando ljust().
        Para garantizar que seek(num_registro * RECORD_SIZE) coincida exactamente en bytes y caracteres,
        normaliza caracteres multibyte si los hubiera.
        """
        clean = str(text).replace("\n", " ").replace("\r", " ").strip()
        # Si algún carácter ocupa más de 1 byte en UTF-8, se reemplaza por su equivalente ASCII seguro
        # para garantizar que 120 caracteres sean siempre exactamente 120 bytes en disco.
        safe_chars = []
        for ch in clean:
            if len(ch.encode("utf-8")) == 1:
                safe_chars.append(ch)
            else:
                replacements = {
                    "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
                    "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U",
                    "ñ": "n", "Ñ": "N", "ü": "u", "Ü": "U"
                }
                safe_chars.append(replacements.get(ch, "?"))
        normalized = "".join(safe_chars)[:max_len]
        return normalized.ljust(max_len)

    def format_record(self, contact_id, nombre, telefono, correo, ciudad):
        """
        Rellena cada campo con espacios a la derecha usando ljust() para garantizar
        que todos los registros midan exactamente RECORD_SIZE (120 bytes).
        """
        id_str = self._normalize_fixed_ascii(contact_id, FIELD_LENGTHS["id"])
        nom_str = self._normalize_fixed_ascii(nombre, FIELD_LENGTHS["nombre"])
        tel_str = self._normalize_fixed_ascii(telefono, FIELD_LENGTHS["telefono"])
        cor_str = self._normalize_fixed_ascii(correo, FIELD_LENGTHS["correo"])
        ciu_str = self._normalize_fixed_ascii(ciudad, FIELD_LENGTHS["ciudad"])

        record = f"{id_str}{nom_str}{tel_str}{cor_str}{ciu_str}\n"
        return record

    def parse_record(self, raw_record):
        """
        Desempaqueta una cadena de tamaño fijo en un diccionario con los campos del contacto.
        """
        if not raw_record or len(raw_record) < RECORD_SIZE - 1:
            return None

        pos = 0
        c_id = raw_record[pos:pos + FIELD_LENGTHS["id"]].strip()
        pos += FIELD_LENGTHS["id"]

        nombre = raw_record[pos:pos + FIELD_LENGTHS["nombre"]].strip()
        pos += FIELD_LENGTHS["nombre"]

        telefono = raw_record[pos:pos + FIELD_LENGTHS["telefono"]].strip()
        pos += FIELD_LENGTHS["telefono"]

        correo = raw_record[pos:pos + FIELD_LENGTHS["correo"]].strip()
        pos += FIELD_LENGTHS["correo"]

        ciudad = raw_record[pos:pos + FIELD_LENGTHS["ciudad"]].strip()

        return {
            "id": int(c_id) if c_id.isdigit() else c_id,
            "nombre": nombre,
            "telefono": telefono,
            "correo": correo,
            "ciudad": ciudad
        }

    def add_contact(self, contact_id, nombre, telefono, correo, ciudad):
        """
        Agrega un nuevo contacto al final del archivo usando seek() y tell(),
        actualiza el índice primario (indice.json) y recalcula el hash SHA-256 (contactos.sha256).
        """
        id_key = str(int(contact_id))
        if id_key in self.index:
            raise ValueError(f"Ya existe un contacto registrado con el ID {id_key}.")

        self._ensure_file_exists()
        record = self.format_record(id_key, nombre, telefono, correo, ciudad)

        try:
            with open(self.filename, "r+", encoding="utf-8", newline="\n") as f:
                f.seek(0, os.SEEK_END)
                byte_offset = f.tell()
                record_number = byte_offset // RECORD_SIZE

                f.write(record)
                new_pos = f.tell()
        except PermissionError as e:
            raise PermissionError(f"No hay permisos de escritura sobre '{self.filename}'.") from e
        except OSError as e:
            raise OSError(f"Error al escribir en '{self.filename}': {e}") from e

        self.index[id_key] = record_number
        self.save_index()
        new_hash = self.save_hash()

        print(f"INFO: Contacto ID {id_key} guardado en registro #{record_number} (offset: {byte_offset}, tell final: {new_pos})")
        return record_number, byte_offset, new_hash

    def search_by_id(self, contact_id):
        """
        Busca un contacto por su ID consultando primero el índice primario (indice.json)
        y luego usando seek(numero_de_registro * RECORD_SIZE) para ir directamente a su posición.
        """
        id_key = str(int(contact_id))
        if id_key not in self.index:
            return None

        record_number = self.index[id_key]
        contact, byte_offset, end_pos = self.read_record_by_number(record_number)
        if contact:
            contact["registro"] = record_number
            contact["offset"] = byte_offset
            contact["tell_after_read"] = end_pos
        return contact

    def update_contact(self, contact_id, nombre, telefono, correo, ciudad):
        """
        Modificación en el lugar (in-place):
        Consulta el número de registro en el índice, usa seek() para posicionarse exactamente
        en ese registro, sobrescribe únicamente esos 120 bytes y actualiza el hash SHA-256.
        """
        id_key = str(int(contact_id))
        if id_key not in self.index:
            raise KeyError(f"No existe ningún contacto con el ID {id_key} en el índice.")

        record_number = self.index[id_key]
        target_offset = record_number * RECORD_SIZE
        record = self.format_record(id_key, nombre, telefono, correo, ciudad)

        try:
            with open(self.filename, "r+", encoding="utf-8", newline="\n") as f:
                f.seek(target_offset)
                start_pos = f.tell()
                f.write(record)
                end_pos = f.tell()
        except PermissionError as e:
            raise PermissionError(f"No hay permisos de escritura para modificar '{self.filename}'.") from e
        except OSError as e:
            raise OSError(f"Error al sobrescribir el registro en '{self.filename}': {e}") from e

        new_hash = self.save_hash()

        print(
            f"INFO: Contacto ID {id_key} modificado in-place en registro #{record_number} "
            f"(tell inicio: {start_pos}, tell fin: {end_pos})"
        )
        return record_number, start_pos, end_pos, new_hash

    def read_record_by_number(self, record_number):
        """
        Lee un contacto directamente calculando su posición (record_number * RECORD_SIZE)
        sin recorrer el archivo completo.
        """
        if not os.path.exists(self.filename):
            return None, 0, 0

        target_offset = record_number * RECORD_SIZE

        try:
            with open(self.filename, "r", encoding="utf-8", newline="\n") as f:
                f.seek(target_offset)
                current_pos = f.tell()
                raw_data = f.read(RECORD_SIZE)
                end_pos = f.tell()
        except PermissionError as e:
            raise PermissionError(f"Sin permisos de lectura en '{self.filename}'.") from e
        except UnicodeDecodeError as e:
            raise ValueError(f"Archivo '{self.filename}' corrupto (codificación UTF-8 inválida).") from e

        if not raw_data:
            return None, current_pos, end_pos

        contact = self.parse_record(raw_data)
        return contact, current_pos, end_pos

    def get_all_contacts(self):
        """
        Lee los registros existentes para mostrarlos en la tabla, manejando posibles errores de archivo.
        """
        contacts = []
        if not os.path.exists(self.filename):
            return contacts

        try:
            with open(self.filename, "r", encoding="utf-8", newline="\n") as f:
                record_num = 0
                while True:
                    f.seek(record_num * RECORD_SIZE)
                    pos = f.tell()
                    data = f.read(RECORD_SIZE)
                    if not data or len(data) < RECORD_SIZE - 1:
                        break
                    parsed = self.parse_record(data)
                    if parsed:
                        parsed["registro"] = record_num
                        parsed["offset"] = pos
                        contacts.append(parsed)
                    record_num += 1
        except PermissionError:
            self.last_error = f"Sin permisos de lectura para '{self.filename}'."
            print(f"ERROR: {self.last_error}")
        except UnicodeDecodeError:
            self.last_error = f"El archivo '{self.filename}' contiene bytes corruptos fuera de UTF-8."
            print(f"ERROR: {self.last_error}")
        except OSError as e:
            self.last_error = f"Error al leer '{self.filename}': {e}"
            print(f"ERROR: {self.last_error}")

        return contacts

    def export_to_json(self, output_file=EXPORT_JSON_FILE):
        """
        Exporta todos los contactos del archivo de registros fijos (contactos.dat)
        a un archivo JSON estructurado en UTF-8, incluyendo metadatos de exportación.
        """
        contacts = self.get_all_contacts()
        export_payload = {
            "fecha_exportacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "archivo_origen": self.filename,
            "tamano_registro_fijo": RECORD_SIZE,
            "total_contactos": len(contacts),
            "contactos": [
                {
                    "id": c["id"],
                    "nombre": c["nombre"],
                    "telefono": c["telefono"],
                    "correo": c["correo"],
                    "ciudad": c["ciudad"],
                    "numero_registro": c["registro"],
                    "offset_bytes": c["offset"]
                }
                for c in contacts
            ]
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_payload, f, indent=4, ensure_ascii=False)

        print(f"INFO: {len(contacts)} contactos exportados exitosamente a '{output_file}'.")
        return output_file, len(contacts)

    @staticmethod
    def _safe_latin1(text):
        """
        Asegura compatibilidad con las fuentes estándar de FPDF (latin-1).
        """
        return str(text).encode("latin-1", "replace").decode("latin-1")

    def generate_pdf_from_json(self, pdf_file=REPORT_PDF_FILE, json_file=EXPORT_JSON_FILE):
        """
        Exporta (o actualiza) primero el archivo JSON y, a partir de ese JSON,
        genera un reporte PDF con tabla formateada y fecha de generación usando fpdf2.
        """
        self.export_to_json(json_file)

        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        contacts_list = json_data.get("contactos", [])
        fecha_export = json_data.get("fecha_exportacion", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        pdf = ContactReportPDF(orientation="P", unit="mm", format="A4")
        pdf.alias_nb_pages()
        pdf.add_page()

        pdf.set_fill_color(255, 243, 224)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(78, 52, 46)
        pdf.cell(
            0,
            8,
            self._safe_latin1(
                f"Origen de datos: {os.path.basename(json_file)}  |  "
                f"Total de contactos: {len(contacts_list)}  |  "
                f"Exportado: {fecha_export}"
            ),
            border=1,
            new_x="LMARGIN",
            new_y="NEXT",
            fill=True
        )
        pdf.ln(4)

        col_widths = [12, 16, 15, 45, 28, 48, 26]
        headers = ["#Reg", "Offset", "ID", "Nombre", "Telefono", "Correo", "Ciudad"]

        pdf.set_fill_color(216, 67, 21)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)

        for width, title in zip(col_widths, headers):
            pdf.cell(width, 8, title, border=1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(30, 20, 15)

        if not contacts_list:
            pdf.cell(sum(col_widths), 10, "No hay contactos registrados para mostrar.", border=1, align="C")
            pdf.ln()
        else:
            for idx, c in enumerate(contacts_list):
                fill_row = (idx % 2 == 1)
                if fill_row:
                    pdf.set_fill_color(255, 248, 240)
                else:
                    pdf.set_fill_color(255, 255, 255)

                row_values = [
                    str(c.get("numero_registro", idx)),
                    f"{c.get('offset_bytes', idx * RECORD_SIZE)}B",
                    str(c.get("id", "")),
                    self._safe_latin1(c.get("nombre", ""))[:24],
                    self._safe_latin1(c.get("telefono", ""))[:15],
                    self._safe_latin1(c.get("correo", ""))[:28],
                    self._safe_latin1(c.get("ciudad", ""))[:15],
                ]

                aligns = ["C", "C", "C", "L", "C", "L", "L"]
                for width, val, align in zip(col_widths, row_values, aligns):
                    pdf.cell(width, 7, val, border=1, align=align, fill=True)
                pdf.ln()

        pdf.output(pdf_file)
        print(f"INFO: Reporte PDF generado exitosamente en '{pdf_file}' a partir de '{json_file}'.")
        return pdf_file, len(contacts_list)

    def create_zip_backup(self, zip_filepath=BACKUP_ZIP_FILE):
        """
        Crea un archivo de respaldo comprimido (.zip) usando el módulo zipfile
        incluyendo el archivo de contactos (contactos.dat) y el índice (indice.json).
        Retorna información detallada del tamaño original y tamaño comprimido.
        """
        if not os.path.exists(self.filename):
            raise FileNotFoundError(f"El archivo '{self.filename}' no existe para respaldar.")
        if not os.path.exists(self.index_filename):
            self.save_index()

        contacts_size = os.path.getsize(self.filename)
        index_size = os.path.getsize(self.index_filename) if os.path.exists(self.index_filename) else 0
        original_total = contacts_size + index_size

        with zipfile.ZipFile(zip_filepath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zf.write(self.filename, arcname=os.path.basename(self.filename))
            if os.path.exists(self.index_filename):
                zf.write(self.index_filename, arcname=os.path.basename(self.index_filename))

        compressed_size = os.path.getsize(zip_filepath)
        ratio = (1 - (compressed_size / original_total)) * 100 if original_total > 0 else 0.0

        info = {
            "zip_path": zip_filepath,
            "contacts_size": contacts_size,
            "index_size": index_size,
            "original_size": original_total,
            "compressed_size": compressed_size,
            "reduction_percent": ratio
        }
        print(
            f"INFO: Respaldo ZIP creado en '{zip_filepath}' "
            f"(Original: {original_total} B -> Comprimido: {compressed_size} B, Ahorro: {ratio:.1f}%)"
        )
        return info

    def get_file_metadata(self):
        """
        Obtiene los metadatos y permisos de contactos.dat e indice.json
        utilizando os.stat() y os.access().
        """
        result = {}
        for label, path in [("contactos", self.filename), ("indice", self.index_filename), ("hash", self.hash_filename)]:
            if not os.path.exists(path):
                result[label] = {
                    "nombre": path,
                    "existe": False,
                    "tamano_bytes": 0,
                    "ultima_modificacion": "No existe",
                    "ultimo_acceso": "No existe",
                    "permiso_lectura": False,
                    "permiso_escritura": False,
                    "modo_octal": "N/A"
                }
                continue

            st = os.stat(path)
            can_read = os.access(path, os.R_OK)
            can_write = os.access(path, os.W_OK)

            result[label] = {
                "nombre": path,
                "ruta_absoluta": os.path.abspath(path),
                "existe": True,
                "tamano_bytes": st.st_size,
                "ultima_modificacion": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "ultimo_acceso": datetime.fromtimestamp(st.st_atime).strftime("%Y-%m-%d %H:%M:%S"),
                "permiso_lectura": can_read,
                "permiso_escritura": can_write,
                "modo_octal": oct(st.st_mode)[-4:]
            }

        result["total_registros"] = (
            result["contactos"]["tamano_bytes"] // RECORD_SIZE if result["contactos"]["existe"] else 0
        )
        result["tamano_registro_fijo"] = RECORD_SIZE
        return result
