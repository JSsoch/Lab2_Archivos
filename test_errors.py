import os
import stat
import sys
from datetime import datetime
from contact_manager import (
    ContactManager,
    CONTACTS_FILE,
    INDEX_FILE,
    HASH_FILE,
    EXPORT_JSON_FILE,
    REPORT_PDF_FILE,
    BACKUP_ZIP_FILE,
    RECORD_SIZE
)


def run_all_tests_and_seed():
    log_lines = []

    def log(msg):
        print(msg)
        log_lines.append(msg)

    log("======================================================================")
    log("BATERÍA DE PRUEBAS Y GENERACIÓN DE ENTREGABLES - LABORATORIO NO. 2")
    log(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("======================================================================\n")

    # Limpieza previa para iniciar con estado limpio
    for f in [CONTACTS_FILE, INDEX_FILE, HASH_FILE, EXPORT_JSON_FILE, REPORT_PDF_FILE, BACKUP_ZIP_FILE]:
        if os.path.exists(f):
            try:
                os.chmod(f, stat.S_IWRITE | stat.S_IREAD)
                os.remove(f)
            except Exception:
                pass

    log("--- 1. PRUEBA DE INICIALIZACIÓN CON ARCHIVOS INEXISTENTES ---")
    manager = ContactManager()
    log(f"Archivo '{CONTACTS_FILE}' inicializado correctamente (Tamaño: {os.path.getsize(CONTACTS_FILE)} bytes).\n")

    log("--- 2. INSERCIÓN DE CONTACTOS (REGISTROS DE TAMAÑO FIJO = 120 BYTES) ---")
    sample_contacts = [
        (101, "Josue Soch", "5544-1122", "jsoch@correo.url.edu.gt", "Quetzaltenango"),
        (102, "Maria Fernanda Lopez", "4433-2211", "mflopez@correo.url.edu.gt", "Guatemala"),
        (105, "Carlos Eduardo Ruiz", "3322-8899", "ceruiz@correo.url.edu.gt", "Totonicapan"),
        (108, "Ana Lucia Morales", "7766-5544", "almorales@correo.url.edu.gt", "San Marcos"),
        (112, "Diego Alejandro Perez", "5511-9900", "daperez@correo.url.edu.gt", "Huehuetenango"),
        (115, "Sofia Gabriela Gomez", "4488-7766", "sggomez@correo.url.edu.gt", "Retalhuleu"),
        (120, "Luis Fernando Castillo", "3399-4455", "lfcastillo@correo.url.edu.gt", "Mazatenango"),
        (125, "Valeria Alejandra Diaz", "7722-3344", "vadiaz@correo.url.edu.gt", "Antigua Guatemala"),
    ]

    for cid, nom, tel, cor, ciu in sample_contacts:
        rec_num, offset, new_hash = manager.add_contact(cid, nom, tel, cor, ciu)
        log(f" -> Agregado ID {cid}: Registro #{rec_num} | seek/tell offset: {offset} B | SHA-256: {new_hash[:16]}...")

    log("\n--- 3. BÚSQUEDA DIRECTA POR ID MEDIANTE ÍNDICE PRIMARIO (indice.json) ---")
    found = manager.search_by_id(108)
    log(
        f" -> Búsqueda ID 108 en indice.json: Registro #{found['registro']} | "
        f"seek({found['offset']}) | tell() fin: {found['tell_after_read']} | Nombre: {found['nombre']}"
    )
    not_found = manager.search_by_id(999)
    log(f" -> Búsqueda ID 999 (inexistente): Resultado = {not_found} (Controlado sin errores)\n")

    log("--- 4. MODIFICACIÓN EN EL LUGAR (IN-PLACE) CON seek() Y tell() ---")
    size_before = os.path.getsize(CONTACTS_FILE)
    rec_n, t_start, t_end, u_hash = manager.update_contact(
        105, "Carlos E. Ruiz Modificado", "3322-0000", "carlos.ruiz@url.edu.gt", "Quetzaltenango"
    )
    size_after = os.path.getsize(CONTACTS_FILE)
    log(
        f" -> Modificado ID 105 en Registro #{rec_n}: seek({t_start}) -> tell({t_end}) | "
        f"Tamaño archivo antes: {size_before} B, después: {size_after} B"
    )
    log(f" -> Nuevo Hash SHA-256 guardado en '{HASH_FILE}': {u_hash}\n")

    log("--- 5. PRUEBA DE DETECCIÓN DE ALTERACIÓN MANUAL (INTEGRIDAD SHA-256) ---")
    with open(CONTACTS_FILE, "rb") as f:
        original_bytes = f.read()

    # Simulamos alteración externa cambiando un carácter directamente en el archivo
    tampered_bytes = bytearray(original_bytes)
    tampered_bytes[6] = ord("X")
    with open(CONTACTS_FILE, "wb") as f:
        f.write(tampered_bytes)

    is_ok, calc_hash, saved_hash, alert_msg = manager.verify_integrity()
    log(f" -> Estado tras alteración manual externa: es_integro={is_ok}")
    log(f" -> Hash esperado (contactos.sha256): {saved_hash}")
    log(f" -> Hash calculado (archivo alterado): {calc_hash}")
    log(f" -> Mensaje del sistema: {alert_msg}")

    # Restauramos el contenido legítimo para dejar los archivos entregables íntegros
    with open(CONTACTS_FILE, "wb") as f:
        f.write(original_bytes)
    is_ok_restored, _, _, ok_msg = manager.verify_integrity()
    log(f" -> Archivo restaurado a su estado íntegro: es_integro={is_ok_restored} ({ok_msg})\n")

    log("--- 6. PRUEBA DE RECUPERACIÓN ANTE ÍNDICE CORRUPTO ---")
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write("{json_corrupto_invalido:")
    manager.load_index()
    log(f" -> Índice reconstruido exitosamente tras corrupción: {len(manager.index)} entradas activas.\n")

    log("--- 7. EXPORTACIÓN A JSON, REPORTE PDF Y RESPALDO ZIP ---")
    json_path, total_json = manager.export_to_json(EXPORT_JSON_FILE)
    pdf_path, total_pdf = manager.generate_pdf_from_json(REPORT_PDF_FILE, EXPORT_JSON_FILE)
    zip_info = manager.create_zip_backup(BACKUP_ZIP_FILE)

    log(f" -> Exportado JSON: {json_path} ({os.path.getsize(json_path)} bytes)")
    log(f" -> Reporte PDF: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
    log(
        f" -> Respaldo ZIP: {zip_info['zip_path']} | "
        f"Original ({CONTACTS_FILE} + {INDEX_FILE}): {zip_info['original_size']} bytes vs "
        f"Comprimido: {zip_info['compressed_size']} bytes (Reducción: {zip_info['reduction_percent']:.2f}%)\n"
    )

    log("--- 8. METADATOS Y PERMISOS (os.stat y os.access) ---")
    meta = manager.get_file_metadata()
    c_meta = meta["contactos"]
    log(f" -> Archivo: {c_meta['nombre']} | Tamaño: {c_meta['tamano_bytes']} B | Modificado: {c_meta['ultima_modificacion']}")
    log(f" -> Permiso Lectura (R_OK): {c_meta['permiso_lectura']} | Permiso Escritura (W_OK): {c_meta['permiso_escritura']} | Modo: {c_meta['modo_octal']}")

    log("\n======================================================================")
    log("PRUEBAS Y ARCHIVOS ENTREGABLES GENERADOS EXITOSAMENTE")
    log("======================================================================")

    with open("logs.txt", "w", encoding="utf-8") as lf:
        lf.write("\n".join(log_lines) + "\n")


if __name__ == "__main__":
    run_all_tests_and_seed()
