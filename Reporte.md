# Universidad Rafael Landívar
### Campus San Alberto Hurtado, S.J. de Quetzaltenango — Facultad de Ingeniería
**Estudiante:** Josué Soch | **Carnet:** `1537924` | **Fecha:** Octubre 2026  
**Laboratorio No. 2:** Agenda de Contactos con Acceso Aleatorio

---

## 1. Estructura del Registro Fijo (`120 bytes` en `contactos.dat`)

Cada registro mide exactamente **120 bytes** en UTF-8 rellenando cada campo con espacios mediante `.ljust()`:

| Campo | Largo Fijo | Rango de Bytes | Formato / Relleno |
| :--- | :--- | :--- | :--- |
| **`id`** | 6 caracteres | Bytes 0 – 5 | Entero único (`.ljust(6)`) |
| **`nombre`** | 30 caracteres | Bytes 6 – 35 | Texto (`.ljust(30)`) |
| **`telefono`** | 15 caracteres | Bytes 36 – 50 | Texto (`.ljust(15)`) |
| **`correo`** | 40 caracteres | Bytes 51 – 90 | Texto (`.ljust(40)`) |
| **`ciudad`** | 28 caracteres | Bytes 91 – 118 | Texto (`.ljust(28)`) |
| **Salto (`\n`)** | 1 carácter | Byte 119 | Fin de registro (`1 byte`) |
| **TOTAL** | **120 bytes** | **120 B / reg** | **Longitud fija por contacto** |

---

## 2. Acceso Aleatorio y Modificación In-Place con `seek()` y `tell()`

Fórmula de posición directa: $\text{offset} = \text{num\_registro} \times 120$. Con `seek(offset)` se lee o sobrescribe únicamente ese registro sin recorrer ni reescribir el resto del archivo; `tell()` confirma el byte actual:

```python
def read_record_by_number(self, record_number):
    with open(self.filename, "r", encoding="utf-8", newline="\n") as f:
        f.seek(record_number * 120)     # Salto directo O(1)
        start = f.tell()                # Byte inicial del registro
        data = f.read(120)
        return self.parse_record(data), start, f.tell()

def update_contact(self, contact_id, nombre, telefono, correo, ciudad):
    rec_num = self.index[str(int(contact_id))]
    with open(self.filename, "r+", encoding="utf-8", newline="\n") as f:
        f.seek(rec_num * 120)           # Ubicación exacta del registro
        start = f.tell()
        f.write(self.format_record(contact_id, nombre, telefono, correo, ciudad))  # In-place
```

---

## 3. Índice Primario (`indice.json`) vs. Búsqueda Secuencial

* **Búsqueda Secuencial $\mathcal{O}(N)$:** Recorre línea por línea desde el inicio; en $N$ registros requiere hasta $N$ lecturas.
* **Búsqueda con Índice $\mathcal{O}(1)$:** Consulta el ID en `indice.json` ($\mathcal{O}(1)$ en memoria) y ejecuta un único `seek(reg * 120)`.

```json
{"101": 0, "102": 1, "105": 2, "108": 3, "112": 4, "115": 5, "120": 6, "125": 7}
```

---

## 4. Verificación de Integridad SHA-256 (`contactos.sha256`)

Al modificar manualmente `contactos.dat` fuera de la aplicación (`Josue` $\rightarrow$ `Xosue`), el hash SHA-256 cambia de `12a06fe256c4...` a `c857900f2112...`, disparando inmediatamente la alerta de integridad al iniciar.

---

## 5. Comparación: Archivo Original vs. Respaldo ZIP (`respaldo_agenda.zip`)

| Archivo | Tamaño Original | Tamaño en ZIP | Reducción |
| :--- | :---: | :---: | :---: |
| `contactos.dat` (8 reg $\times$ 120 B) | 960 bytes | Incluido | Espacios `.ljust()` |
| `indice.json` | 123 bytes | Incluido | JSON |
| **TOTAL (`respaldo_agenda.zip`)** | **1,083 bytes** | **642 bytes** | **-441 B (40.72%)** |
