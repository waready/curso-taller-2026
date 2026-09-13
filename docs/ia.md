# Desarrollo asistido por IA

Codex o Claude Code no reemplazan la arquitectura. Los utilizaremos para avanzar en ciclos pequeños y verificables.

## Ciclo de trabajo

1. **Explicar:** pedir que describa el flujo actual sin modificar archivos.
2. **Planear:** solicitar un cambio pequeño y sus archivos afectados.
3. **Editar:** autorizar la implementación.
4. **Probar:** abrir dos o tres navegadores y provocar errores.
5. **Revisar:** pedir que encuentre riesgos y simplifique.

## Prompts listos

### Comprender

```text
Explica este proyecto para un estudiante que conoce Python pero recién aprende
WebSocket. Describe conexión, recepción, broadcast y desconexión. No edites nada.
```

### Implementar

```text
Agrega [FUNCIÓN] reutilizando el WebSocket existente. Primero dame un plan de
máximo 5 pasos. Después modifica solo los archivos necesarios. No agregues
dependencias y conserva la interfaz actual.
```

### Revisar

```text
Revisa los cambios recientes. Busca datos sin validar, conexiones que no se
eliminen al cerrar la pestaña y eventos que puedan romper otros clientes.
Propón correcciones pequeñas y ejecuta una verificación de sintaxis.
```

## Para no consumir el presupuesto del grupo

- Un integrante usa el asistente; los demás observan y prueban.
- Enviar una tarea concreta, no “haz todo el proyecto”.
- Pedir primero una explicación corta.
- Adjuntar solo los archivos relevantes.
- Detenerse después de una función que ya funciona.

::: danger Nunca hacer
No pegues claves API en el chat, en el código ni en un archivo `.env` que vaya a Git. Si una clave aparece en una captura o repositorio, debe revocarse.
:::
