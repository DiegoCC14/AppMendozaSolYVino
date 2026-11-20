# Ejecutar GitHub Actions con Cronojobs

Cronojobs permite activar el workflow `schedule.yml` del repositorio `DiegoCC14/AppMendozaSolYVino` mediante la API de GitHub.

## Configuración

- **Método:** `POST`
- **URL:**

  ```text
  https://api.github.com/repos/DiegoCC14/AppMendozaSolYVino/actions/workflows/schedule.yml/dispatches
  ```

- **Headers:**

  | Key | Value |
  |---|---|
  | `Authorization` | `Bearer TU_TOKEN_DE_GITHUB` |
  | `Accept` | `application/vnd.github+json` |
  | `X-GitHub-Api-Version` | `2026-03-10` |
  | `Content-Type` | `application/json` |

- **Body (JSON):**

  ```json
  {
    "ref": "main"
  }
  ```

## Crear el token de GitHub

1. Entrar en [GitHub → Developer settings → Personal access tokens](https://github.com/settings/personal-access-tokens).
2. Crear un **Fine-grained token** limitado al repositorio `AppMendozaSolYVino`.
3. En permisos del repositorio, seleccionar **Actions: Read and write**.
4. Usar el token en el header `Authorization` como `Bearer TU_TOKEN_DE_GITHUB`.

No publiques ni compartas el token.

## Prueba

**Recordatorio:** en Postman hay una demo de la solicitud para probar la configuración antes de programarla en Cronojobs.

Después de ejecutar la tarea, revisar la pestaña [Actions del repositorio](https://github.com/DiegoCC14/AppMendozaSolYVino/actions) para verificar que se inició el workflow.
