import os

CONTACTS_FILE = "contactos.dat"

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
    Versión inicial: Estructura de registro fijo y operaciones básicas con seek() y tell().
    """

    def __init__(self, filename=CONTACTS_FILE):
        self.filename = filename
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8", newline="\n") as f:
                pass
            print(f"INFO: Archivo '{self.filename}' creado exitosamente.")

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
        Agrega un nuevo contacto al final del archivo usando seek() y tell().
        """
        record = self.format_record(contact_id, nombre, telefono, correo, ciudad)

        with open(self.filename, "r+", encoding="utf-8", newline="\n") as f:
            # Nos desplazamos al final del archivo
            f.seek(0, os.SEEK_END)
            byte_offset = f.tell()
            record_number = byte_offset // RECORD_SIZE

            f.write(record)
            new_pos = f.tell()

        print(f"INFO: Contacto ID {contact_id} guardado en registro #{record_number} (offset inicial: {byte_offset}, tell final: {new_pos})")
        return record_number, byte_offset

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

        if not raw_data:
            return None, current_pos

        contact = self.parse_record(raw_data)
        return contact, current_pos

    def get_all_contacts(self):
        """
        Lee los registros existentes para mostrarlos en la tabla inicial.
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
