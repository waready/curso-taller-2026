# Python esencial para el taller

<div class="module-banner">
  <span class="eyebrow">Módulo 0 · 30 minutos</span>
  <h2>La sintaxis necesaria para comprender las ocho demos</h2>
  <p>Aprenderemos cada concepto con fragmentos pequeños y luego reconoceremos la misma idea dentro de FastAPI y WebSocket.</p>
</div>

No es un curso completo de Python. Es una ruta práctica para que todos puedan leer, modificar y explicar el código de la sesión.

## Ruta rápida

| Tiempo | Tema | Resultado |
|---:|---|---|
| 5 min | Variables y tipos | Representar usuarios, mensajes y estados. |
| 7 min | Listas, diccionarios y conjuntos | Guardar conexiones y eventos. |
| 6 min | Condiciones, ciclos y funciones | Validar y transformar datos. |
| 5 min | Clases, imports y decoradores | Comprender los administradores de conexión. |
| 7 min | `async` y `await` | Entender por qué el servidor no bloquea a los demás usuarios. |

## 1. Reglas mínimas de sintaxis

Python utiliza **indentación** para organizar los bloques. Usaremos cuatro espacios y no mezclaremos espacios con tabulaciones.

```python
nombre = "Lucía"

if nombre:
    print(f"Conectado: {nombre}")
```

- No se escribe `;` al final.
- Los bloques comienzan con `:`.
- Los comentarios comienzan con `#`.
- Python diferencia mayúsculas y minúsculas: `mensaje` y `Mensaje` no son iguales.

## 2. Variables y tipos de datos

```python
usuario = "Ana"          # str
conexiones = 3            # int
latencia = 18.5           # float
activo = True             # bool
ultimo_evento = None      # sin valor todavía
```

Podemos consultar el tipo con `type()`:

```python
print(type(usuario))
print(type(conexiones))
```

### Texto y f-strings

```python
nombre = "Mateo"
mensaje = "Hola"
salida = f"{nombre} dice: {mensaje}"
print(salida)
```

Las f-strings se usarán para construir mensajes y registros fáciles de leer.

## 3. Colecciones que usaremos

### Lista: mantiene elementos en orden

```python
mensajes = ["Hola", "¿Cómo están?"]
mensajes.append("Empezamos")

print(mensajes[0])
print(len(mensajes))
```

### Diccionario: organiza información por claves

```python
evento = {
    "tipo": "chat",
    "usuario": "Ana",
    "texto": "Hola al grupo",
}

print(evento["tipo"])
print(evento.get("texto", ""))
```

Un diccionario de Python se convierte fácilmente en un objeto JSON para enviarlo por WebSocket.

### Conjunto: evita elementos repetidos

```python
usuarios = {"Ana", "Luis"}
usuarios.add("Ana")

print(usuarios)  # Ana aparece una sola vez
```

En los proyectos se utilizan listas o conjuntos para mantener las conexiones activas.

## 4. Condiciones

```python
evento = {"tipo": "chat", "texto": "Hola"}

if evento["tipo"] == "chat" and evento["texto"]:
    print("Mensaje válido")
elif evento["tipo"] == "salir":
    print("El usuario salió")
else:
    print("Evento desconocido")
```

Operadores frecuentes:

| Operador | Significado | Ejemplo |
|:---:|---|---|
| `==` | Es igual a | `tipo == "chat"` |
| `!=` | Es diferente de | `usuario != ""` |
| `>` / `<` | Mayor o menor | `x < ancho` |
| `and` | Ambas condiciones | `x >= 0 and y >= 0` |
| `or` | Al menos una condición | `tipo == "chat" or tipo == "join"` |
| `not` | Niega una condición | `not conectado` |
| `in` | Está contenido | `tipo in permitidos` |

## 5. Ciclos

```python
conexiones = ["cliente-1", "cliente-2", "cliente-3"]

for conexion in conexiones:
    print(f"Enviar evento a {conexion}")
```

El `for` representa la idea del **broadcast**: recorrer todas las conexiones y enviar el mismo cambio.

```python
contador = 0

while contador < 3:
    contador += 1
    print(contador)
```

## 6. Funciones y retorno

```python
def crear_evento(usuario: str, texto: str) -> dict:
    return {
        "tipo": "chat",
        "usuario": usuario,
        "texto": texto.strip(),
    }

evento = crear_evento("Ana", "  Hola  ")
print(evento)
```

Los parámetros reciben datos; `return` devuelve el resultado. Las anotaciones `str` y `dict` ayudan a leer el código, pero no reemplazan la validación.

## 7. Clases y objetos

Las demos agrupan las conexiones y el broadcast en una clase administradora.

```python
class Sala:
    def __init__(self) -> None:
        self.usuarios: list[str] = []

    def conectar(self, nombre: str) -> None:
        self.usuarios.append(nombre)

    def cantidad(self) -> int:
        return len(self.usuarios)


sala = Sala()
sala.conectar("Ana")
print(sala.cantidad())
```

- `class Sala` define la plantilla.
- `__init__` prepara el estado inicial.
- `self` representa el objeto actual.
- `sala = Sala()` crea una instancia.

## 8. Imports y módulos

```python
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse

app = FastAPI()
```

`import` permite utilizar código de otros módulos. FastAPI y Uvicorn se instalan desde `requirements.txt`.

## 9. Decoradores de FastAPI

```python
@app.get("/")
async def inicio() -> dict:
    return {"estado": "listo"}


@app.websocket("/ws")
async def canal(websocket: WebSocket) -> None:
    await websocket.accept()
```

Un decorador comienza con `@` y registra la función como una ruta HTTP o WebSocket.

## 10. `async` y `await`

Un servidor atiende muchas conexiones. Mientras una conexión espera un mensaje, las demás deben continuar trabajando.

```python
async def escuchar(websocket: WebSocket) -> dict:
    evento = await websocket.receive_json()
    return evento
```

- `async def` declara una función asíncrona.
- `await` espera una operación de entrada/salida sin bloquear todo el servidor.
- Solo se usa `await` dentro de una función `async`.

Broadcast simplificado:

```python
async def broadcast(conexiones: list[WebSocket], evento: dict) -> None:
    for conexion in conexiones:
        await conexion.send_json(evento)
```

## 11. Manejo de errores

```python
try:
    evento = await websocket.receive_json()
except ValueError:
    await websocket.send_json({"tipo": "error", "detalle": "JSON inválido"})
```

En WebSocket también controlaremos la desconexión para retirar al cliente sin detener el servidor.

## 12. Entorno virtual y paquetes

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

El entorno virtual mantiene las dependencias del curso separadas de otros proyectos.

## Del concepto al proyecto

| Python | Uso en las demos |
|---|---|
| Variable | Nombre del usuario, color, voto o posición. |
| Lista o conjunto | Conexiones WebSocket activas. |
| Diccionario | Evento JSON y estado compartido. |
| Condición | Validar mensajes, votos, coordenadas y ofertas. |
| Ciclo `for` | Enviar un evento a todos los clientes. |
| Función | Separar conexión, desconexión y broadcast. |
| Clase | Administrar usuarios y estado del proyecto. |
| `async` / `await` | Atender múltiples conexiones sin bloquear. |
| Decorador | Crear rutas HTTP y WebSocket con FastAPI. |

## Ejercicio 1 — crear un evento

Completa la función para que produzca un diccionario válido:

```python
def crear_reaccion(usuario: str, emoji: str) -> dict:
    # Escribe aquí el return
    pass


print(crear_reaccion("Ana", "🔥"))
```

Resultado esperado:

```python
{"tipo": "reaction", "usuario": "Ana", "emoji": "🔥"}
```

::: details Ver solución
```python
def crear_reaccion(usuario: str, emoji: str) -> dict:
    return {
        "tipo": "reaction",
        "usuario": usuario,
        "emoji": emoji,
    }
```
:::

## Ejercicio 2 — validar una coordenada

```python
def coordenada_valida(x: int, y: int, ancho: int, alto: int) -> bool:
    # Debe devolver True solamente si el punto está dentro del tablero
    pass
```

::: details Ver solución
```python
def coordenada_valida(x: int, y: int, ancho: int, alto: int) -> bool:
    return 0 <= x < ancho and 0 <= y < alto
```
:::

## Comprobación rápida

Antes de continuar, cada estudiante debe poder explicar:

- Por qué un evento se representa con un diccionario.
- Para qué sirve una clase administradora.
- Qué hace el ciclo `for` durante un broadcast.
- Por qué WebSocket utiliza `async` y `await`.

[Continuar con FastAPI y WebSocket →](/laboratorio-websocket.html)
