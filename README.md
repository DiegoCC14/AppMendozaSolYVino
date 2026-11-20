# Activar un workflow de GitHub Actions con Cronojobs

Esta guía explica cómo configurar un servicio de tareas programadas (Cronojobs) para ejecutar el workflow `schedule.yml` del repositorio `DiegoCC14/AppMendozaSolYVino` mediante la API REST de GitHub.

> **Importante:** consultar el workflow y ejecutarlo son dos operaciones diferentes. La URL indicada sin `/dispatches` sirve para consultar el workflow (`GET`). Para iniciarlo, se debe enviar una solicitud `POST` al endpoint que termina en `/dispatches`.

## 1. Verificar que el workflow existe

El workflow está en:

```text
.github/workflows/schedule.yml
```

Debe incluir el evento `workflow_dispatch` para permitir que la API lo ejecute manualmente. Por ejemplo:

```yaml
name: Automatizacion_AppMendozaSolYVino

on:
  schedule:
    - cron: '*/5 * * * *'
  workflow_dispatch:

# ...resto de la configuración del workflow...
```

El evento `schedule` permite que GitHub intente iniciarlo según su cron interno. `workflow_dispatch` permite iniciarlo desde la interfaz de GitHub o mediante la API.

Para consultar los datos del workflow, se puede utilizar este endpoint:

```http
GET https://api.github.com/repos/DiegoCC14/AppMendozaSolYVino/actions/workflows/schedule.yml
```

Una respuesta `200 OK` indica que GitHub pudo consultar el workflow. Este `GET` **no lo ejecuta**.

## 2. Crear un token con acceso limitado en GitHub

Se recomienda usar un **Fine-grained personal access token** limitado a este repositorio.

1. Entrar en [GitHub → Settings → Developer settings](https://github.com/settings/personal-access-tokens).
2. Abrir **Fine-grained tokens** y seleccionar **Generate new token**.
3. En **Resource owner**, seleccionar `DiegoCC14` (el propietario del repositorio).
4. En **Repository access**, elegir **Only select repositories** y seleccionar `AppMendozaSolYVino`.
5. En **Repository permissions**, configurar **Actions: Read and write**.
6. Elegir una fecha de expiración adecuada y generar el token.
7. Copiarlo y guardarlo en un lugar seguro. GitHub normalmente muestra el valor completo solamente al crearlo.

El permiso `Actions: Read and write` es necesario para crear un evento `workflow_dispatch` con un token fine-grained.

**Seguridad:** no pegar el token en este README, en el código del repositorio ni en una URL. Guardarlo en el campo seguro de credenciales/variables del servicio Cronojobs. Si el token se publica por accidente, revocarlo y generar otro.

## 3. Configurar la solicitud en Cronojobs

Crear una tarea HTTP programada con la siguiente configuración.

### Método

```text
POST
```

### URL para ejecutar el workflow

```text
https://api.github.com/repos/DiegoCC14/AppMendozaSolYVino/actions/workflows/schedule.yml/dispatches
```

### Headers

Agregar estos encabezados:

| Key | Value |
|---|---|
| `Authorization` | `Bearer TU_TOKEN_DE_GITHUB` |
| `Accept` | `application/vnd.github+json` |
| `X-GitHub-Api-Version` | `2026-03-10` |
| `Content-Type` | `application/json` |

Reemplazar `TU_TOKEN_DE_GITHUB` por el token creado en el paso anterior. Debe haber un espacio entre `Bearer` y el token.

Si Cronojobs dispone de un campo específico para **Bearer Token**, puede usarse ese campo en lugar de escribir el header manualmente. No configurar la misma autorización dos veces.

### Body

Seleccionar el tipo de contenido JSON y enviar este objeto:

```json
{
  "ref": "main"
}
```

`ref` indica la rama desde la cual GitHub ejecutará el workflow. En este caso se utiliza `main`. No enviar `{main}` ni el texto `main` sin un objeto JSON.

### Frecuencia

Configurar la periodicidad deseada en Cronojobs, por ejemplo, cada 5 minutos. La zona horaria y la sintaxis de programación dependen del servicio Cronojobs elegido.

## 4. Probar la configuración

Ejecutar la tarea manualmente desde Cronojobs, si el servicio ofrece esa opción, y luego abrir:

[Actions del repositorio](https://github.com/DiegoCC14/AppMendozaSolYVino/actions)

Debería aparecer una ejecución nueva del workflow. Al dispararlo mediante este endpoint, el evento se mostrará como `workflow_dispatch`, no como `schedule`.

La API actual documenta `200 OK` como respuesta correcta para crear el evento de ejecución. La respuesta puede incluir el identificador de la ejecución y sus enlaces.

## 5. Ejemplo con cURL

Este ejemplo sirve para probar la misma petición desde una terminal. Reemplazar el marcador del token por la credencial propia; no subir este comando con el token real a GitHub.

```bash
curl --request POST \
  --url "https://api.github.com/repos/DiegoCC14/AppMendozaSolYVino/actions/workflows/schedule.yml/dispatches" \
  --header "Accept: application/vnd.github+json" \
  --header "Authorization: Bearer TU_TOKEN_DE_GITHUB" \
  --header "X-GitHub-Api-Version: 2026-03-10" \
  --header "Content-Type: application/json" \
  --data '{"ref":"main"}'
```

## 6. Errores comunes

| Código | Causa probable | Qué revisar |
|---|---|---|
| `200 OK` | GitHub aceptó la solicitud | Revisar la pestaña Actions para confirmar la ejecución. |
| `401 Unauthorized` | Token inválido, vencido o ausente | Comprobar el token y el header `Authorization`. |
| `403 Forbidden` | Token sin permisos suficientes o sin acceso al repositorio | Confirmar que el token está limitado al repositorio correcto y tiene `Actions: Read and write`. |
| `404 Not Found` | Repositorio o workflow incorrecto, o falta de acceso | Revisar propietario, nombre del repositorio y `schedule.yml`. |
| `422 Unprocessable Entity` | Petición, cuerpo o referencia inválidos; o workflow sin `workflow_dispatch` | Usar `POST` con `/dispatches`, enviar JSON válido `{"ref":"main"}` y confirmar que el evento está en el archivo publicado en `main`. |

## 7. Documentación oficial

- [GitHub REST API: Create a workflow dispatch event](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
- [Crear personal access tokens de permisos granulares](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
