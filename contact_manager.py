import json
import os

CONTACTS_FILE = "contactos.dat"
INDEX_FILE = "indice.json"

# Definición de longitudes fijas para cada campo (Total = 120 caracteres por registro)
# id: 6 | nombre: 30 | telefono: 15 | correo: 40 | ciudad: 28 | salto de línea (\n): 1 -> 120 bytes
FIELD_LENGTHS = {
    "id": 6,
    "nombre": 30,
    "telefono": 15,
    "correo": 40,
    "ciudad": 28
}

RECORD_SIZE = sum(FIELD_LENGTHS.values()) + 1  # 119 caracteres de datos + 1 salto de línea = 120


class ContactManager:
    """
    Gestor de archivos para la agenda de contactos con registros de tamaño fijo.
    Incluye índice primario en JSON (indice.json), búsqueda directa por ID con seek()
    y modificación en el lugar (in-place) sin reescribir el resto del archivo.
    """

    def __init__(self, filename=CONTACTS_FILE, index_filename=INDEX_FILE):
        self.filename = filename
        self.index_filename = index_filename
        self.index = {}
        self._ensure_file_exists()
        self.load_index()

    def _ensure_file_exists(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8", newline="\n") as f:
                pass
            print(f"INFO: Archivo '{self.filename}' creado exitosamente.")

    def load_index(self):
        """
        Carga el índice primario desde indice.json.
        Si el archivo no existe pero contactos.dat tiene datos, reconstruye el índice.
        """
        if not os.path.exists(self.index_filename):
            self.index = {}
            self.rebuild_index()
            return

        try:
            with open(self.index_filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Normalizar claves como string de ID y valores como entero de número de registro
                self.index = {str(k): int(v) for k, v in data.items()}
            print(f"INFO: Índice cargado desde '{self.index_filename}' ({len(self.index)} registros).")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"WARN: Archivo de índice corrupto ({e}). Reconstruyendo desde '{self.filename}'...")
            self.rebuild_index()

    def save_index(self):
        """
        Guarda el diccionario de índice primario {id: numero_de_registro} en indice.json.
        """
        with open(self.index_filename, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=4, ensure_ascii=False)

    def rebuild_index(self):
        """
        Recorre los registros de tamaño fijo para reconstruir el índice primario si no existe o se corrompió.
        """
        self.index = {}
        if not os.path.exists(self.filename):
            self.save_index()
            return

        with open(self.filename, "r", encoding="utf-8", newline="\n") as f:
            record_num = 0
            while True:
                f.seek(record_num * RECORD_SIZE)
                raw_data = f.read(RECORD_SIZE)
                if not raw_data or len(raw_data) < RECORD_SIZE - 1:
                    break
                parsed = self.parse_record(raw_data)
                if parsed and parsed["id"] != "":
                    self.index[str(parsed["id"])] = record_num
                record_num += 1

        self.save_index()

    def format_record(self, contact_id, nombre, telefono, correo, ciudad):
        """
        Rellena cada campo con espacios a la derecha usando ljust() para garantizar
        que todos los registros midan exactamente RECORD_SIZE (120 caracteres).
        """
        id_str = str(contact_id).strip()[:FIELD_LENGTHS["id"]].ljust(FIELD_LENGTHS["id"])
        nom_str = str(nombre).strip()[:FIELD_LENGTHS["nombre"]].ljust(FIELD_LENGTHS["nombre"])
        tel_str = str(telefono).strip()[:FIELD_LENGTHS["telefono"]].ljust(FIELD_LENGTHS["telefono"])
        cor_str = str(correo).strip()[:FIELD_LENGTHS["correo"]].ljust(FIELD_LENGTHS["correo"])
        ciu_str = str(ciudad).strip()[:FIELD_LENGTHS["ciudad"]].ljust(FIELD_LENGTHS["ciudad"])

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
        validando en el índice primario que el ID sea único y actualizando indice.json.
        """
        id_key = str(int(contact_id))
        if id_key in self.index:
            raise ValueError(f"Ya existe un contacto registrado con el ID {id_key}.")

        record = self.format_record(id_key, nombre, telefono, correo, ciudad)

        with open(self.filename, "r+", encoding="utf-8", newline="\n") as f:
            f.seek(0, os.SEEK_END)
            byte_offset = f.tell()
            record_number = byte_offset // RECORD_SIZE

            f.write(record)
            new_pos = f.tell()

        # Actualizar índice primario y guardarlo en JSON
        self.index[id_key] = record_number
        self.save_index()

        print(f"INFO: Contacto ID {id_key} guardado en registro #{record_number} (offset: {byte_offset}, tell final: {new_pos})")
        return record_number, byte_offset

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
        en ese registro y sobrescribe únicamente esos 120 bytes sin reescribir el resto del archivo.
        """
        id_key = str(int(contact_id))
        if id_key not in self.index:
            raise KeyError(f"No existe ningún contacto con el ID {id_key} en el índice.")

        record_number = self.index[id_key]
        target_offset = record_number * RECORD_SIZE
        record = self.format_record(id_key, nombre, telefono, correo, ciudad)

        with open(self.filename, "r+", encoding="utf-8", newline="\n") as f:
            f.seek(target_offset)
            start_pos = f.tell()
            f.write(record)
            end_pos = f.tell()

        print(
            f"INFO: Contacto ID {id_key} modificado in-place en registro #{record_number} "
            f"(tell inicio: {start_pos}, tell fin: {end_pos})"
        )
        return record_number, start_pos, end_pos

    def read_record_by_number(self, record_number):
        """
        Lee un contacto directamente calculando su posición (record_number * RECORD_SIZE)
        sin recorrer el archivo completo.
        """
        target_offset = record_number * RECORD_SIZE

        with open(self.filename, "r", encoding="utf-8", newline="\n") as f:
            f.seek(target_offset)
            current_pos = f.tell()
            raw_data = f.read(RECORD_SIZE)
            end_pos = f.tell()

        if not raw_data:
            return None, current_pos, end_pos

        contact = self.parse_record(raw_data)
        return contact, current_pos, end_pos

    def get_all_contacts(self):
        """
        Lee los registros existentes para mostrarlos en la tabla.
        """
        contacts = []
        if not os.path.exists(self.filename):
            return contacts

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
        return contacts
