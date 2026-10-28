# Universidad Rafael Landívar
### Campus San Alberto Hurtado, S.J. de Quetzaltenango
### Facultad de Ingeniería | Ingeniería en Informática y Sistemas
**Curso:** Manejo e Implementación de Archivos  
**Laboratorio No. 2:** Agenda de Contactos con Acceso Aleatorio  
**Fecha:** Octubre 2026  

---

## 1. Estructura del Registro de Tamaño Fijo (120 Bytes)

Todos los contactos se almacenan en el archivo `contactos.dat` en codificación UTF-8 utilizando registros de longitud estrictamente fija. Cada campo se rellena con espacios a la derecha mediante el método `.ljust()` hasta completar su largo máximo definido, sumando exactamente **120 bytes por registro**:

| Campo | Longitud Fija | Rango de Bytes | Descripción y Relleno |
| :--- | :--- | :--- | :--- |
| **`id`** | 6 caracteres | Bytes 0 – 5 | Entero único identificador (`str(id).ljust(6)`) |
| **`nombre`** | 30 caracteres | Bytes 6 – 35 | Nombre completo del contacto (`.ljust(30)`) |
| **`telefono`** | 15 caracteres | Bytes 36 – 50 | Número telefónico (`.ljust(15)`) |
| **`correo`** | 40 caracteres | Bytes 51 – 90 | Correo electrónico (`.ljust(40)`) |
| **`ciudad`** | 28 caracteres | Bytes 91 – 118 | Ciudad de residencia (`.ljust(28)`) |
| **Salto (`\n`)** | 1 carácter | Byte 119 | Delimitador de línea fijo (`LF = 1 byte`) |
| **TOTAL** | **120 bytes** | **120 bytes / reg** | **Tamaño constante garantizado por registro** |

---

## 2. Implementación del Acceso Aleatorio e In-Place con `seek()` y `tell()`

Dado que todos los registros miden exactamente `RECORD_SIZE = 120` bytes, la posición exacta (*offset* en bytes) de cualquier registro $N$ se calcula en tiempo constante $\mathcal{O}(1)$ mediante la fórmula:

$$\text{target\_offset} = \text{record\_number} \times 120$$

Con `f.seek(target_offset)` el puntero de archivo salta directamente al byte inicial del contacto sin recorrer los registros previos. Al editar un contacto (**modificación en el lugar / in-place**), se abre el archivo en modo `'r+'` y se sobrescriben únicamente esos 120 bytes sin reescribir el resto del archivo. `f.tell()` se utiliza para verificar e informar al usuario la posición exacta del puntero antes y después de cada operación.

```python
def read_record_by_number(self, record_number):
    target_offset = record_number * RECORD_SIZE  # Ej: Registro #3 * 120 = byte 360
    with open(self.filename, "r", encoding="utf-8", newline="\n") as f:
        f.seek(target_offset)           # Salto directo O(1) sin leer el archivo completo
        current_pos = f.tell()          # Posición inicial antes de leer (ej. 360)
        raw_data = f.read(RECORD_SIZE)  # Lee exactamente 120 bytes
        end_pos = f.tell()              # Posición final tras lectura (ej. 480)
    return self.parse_record(raw_data), current_pos, end_pos

def update_contact(self, contact_id, nombre, telefono, correo, ciudad):
    record_number = self.index[str(int(contact_id))]
    target_offset = record_number * RECORD_SIZE
    record = self.format_record(contact_id, nombre, telefono, correo, ciudad)
    with open(self.filename, "r+", encoding="utf-8", newline="\n") as f:
        f.seek(target_offset)           # Se ubica exactamente en el registro a editar
        start_pos = f.tell()
        f.write(record)                 # Sobrescribe SOLO los 120 bytes de ese contacto
        end_pos = f.tell()
    new_hash = self.save_hash()         # Actualiza firma SHA-256
    return record_number, start_pos, end_pos, new_hash
```

---

## 3. Funcionamiento del Índice Primario (`indice.json`) y Eficiencia

El archivo `indice.json` mantiene un diccionario clave-valor que relaciona cada `id` con su número de registro físico dentro de `contactos.dat`:

```json
{
    "101": 0,
    "102": 1,
    "105": 2,
    "108": 3,
    "112": 4,
    "115": 5,
    "120": 6,
    "125": 7
}
```

### ¿Por qué una búsqueda con índice es más eficiente que una búsqueda secuencial?
* **Búsqueda Secuencial $\mathcal{O}(N)$:** Requiere abrir el archivo y leer línea por línea desde el registro `#0` hasta encontrar el ID buscado. En un archivo con $100,000$ contactos, buscar el último registro implica realizar $100,000$ lecturas de disco.
* **Búsqueda con Índice Primario + `seek()` $\mathcal{O}(1)$:** Consulta primero el ID en la tabla hash en memoria cargada desde `indice.json` (complejidad promedio $\mathcal{O}(1)$) para obtener el número de registro, e inmediatamente ejecuta un único salto `f.seek(numero_registro * 120)` y una única lectura `f.read(120)`.

---

## 4. Verificación de Integridad con Hash SHA-256 (`contactos.sha256`)

Cada vez que se guarda o modifica un contacto, se calcula el resumen criptográfico SHA-256 de `contactos.dat` usando `hashlib.sha256()` y se almacena en `contactos.sha256`. Al iniciar la aplicación se recalcula y compara; cuando se alteró manualmente el Registro `#0` fuera de la aplicación (`Josue` $\rightarrow$ `Xosue`), el hash cambió de `12a06fe256c4efe0ed80bc4f34a14941f37074604b41c211424fc0b6dbdbc51e` a `c857900f2112f6f758e04d999249783f9bd1d79042e1c77120b25f05aeb03ab3`, disparando la alerta de seguridad inmediatamente.

---

## 5. Comparación del Tamaño Original contra el Respaldo ZIP (`respaldo_agenda.zip`)

| Archivo / Métrica | Tamaño Original | Tamaño en ZIP | Ahorro / Reducción |
| :--- | :---: | :---: | :---: |
| `contactos.dat` (8 registros $\times$ 120 B) | 960 bytes | Incluido en ZIP | Espacios comprimidos |
| `indice.json` (8 entradas JSON) | 123 bytes | Incluido en ZIP | Estructura JSON |
| **TOTAL COMPARATIVO (`respaldo_agenda.zip`)** | **1,083 bytes** | **642 bytes** | **-441 bytes (40.72%)** |
