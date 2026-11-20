# Prototipo-Tiempo-es-Vida

Aplicacion de demostracion compuesta por:

- React y Vite como interfaz web.
- Django REST Framework como API.
- PostgreSQL como base de datos.
- Docker Compose para ejecutar los servicios.
- Cloudflare Tunnel para exponer temporalmente puertos locales mediante HTTPS.

No usar este procedimiento con datos reales de pacientes. Las cuentas, registros ECG, resultados y respaldos creados durante una prueba deben considerarse datos de demostracion.

## Ejecucion local

Requisitos:

- Git.
- Docker Desktop o Docker Engine con Docker Compose.
- PowerShell en Windows, o una terminal compatible en macOS/Linux.

Desde la raiz del repositorio:

```powershell
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py cargar_recomendaciones
docker compose exec backend python manage.py createsuperuser
```

Abrir:

```text
http://localhost:5173
```

API local:

```text
http://localhost:8000/api/health/
```

## Preparar una configuracion temporal

El archivo `.env` es local y esta excluido por `.gitignore`.

Desde la raiz del repositorio:

```powershell
Copy-Item .env.example .env
```

En macOS/Linux:

```sh
cp .env.example .env
```

No subir `.env`, claves, respaldos reales ni datos personales al repositorio.

### Generar una clave temporal de Django

Inicie primero los contenedores:

```powershell
docker compose up --build -d
```

Genere una clave:

```powershell
docker compose exec backend python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Reemplace `DJANGO_SECRET_KEY` en `.env` por la salida. Esta clave solo debe durar la demostracion.

## Despliegue temporal publico con Cloudflare Tunnel

Esta opcion no requiere servidor ni pago para usar la demostracion durante varias horas. El equipo debe permanecer encendido y tener conexion a Internet mientras los tuneles esten activos.

Las URLs rapidas de Cloudflare pueden cambiar cuando se reinicia un tunel y no tienen una duracion garantizada ni una cuenta regresiva consultable. En un uso temporal pueden mantenerse disponibles varias horas, pero no representan un despliegue de produccion.

### 1. Instalar cloudflared

Windows mediante winget:

```powershell
winget install --id Cloudflare.cloudflared
```

Si el ejecutable no queda disponible en `PATH`, volver a abrir la terminal o buscarlo en:

```text
C:\Program Files (x86)\cloudflared\cloudflared.exe
```

En macOS:

```sh
brew install cloudflared
```

En Linux, consulte el instalador oficial indicado por Cloudflare para la distribucion utilizada.

### 2. Iniciar Docker y preparar datos

```powershell
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py cargar_recomendaciones
docker compose ps
```

Crear un administrador solo si se necesita:

```powershell
docker compose exec backend python manage.py createsuperuser
```

### 3. Crear el tunel del backend

En una primera terminal independiente:

```powershell
cloudflared tunnel --url http://localhost:8000
```

Copiar la URL HTTPS mostrada por Cloudflare, por ejemplo:

```text
https://backend-ejemplo.trycloudflare.com
```

Comprobarla:

```powershell
curl.exe https://backend-ejemplo.trycloudflare.com/api/health/
```

Debe responder:

```json
{"status":"ok","service":"Tiempo es Vida API"}
```

### 4. Configurar el frontend y Django

Editar `.env` y reemplazar el valor del backend:

```dotenv
VITE_API_BASE_URL=https://backend-ejemplo.trycloudflare.com/api
VITE_ALLOWED_HOSTS=localhost,127.0.0.1,.trycloudflare.com
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=la-clave-generada
DJANGO_ALLOWED_HOSTS=*
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173
```

Para una demostracion temporal, `*` permite que Django responda bajo el hostname de Cloudflare generado. No debe usarse en produccion.

Recrear los contenedores:

```powershell
docker compose up -d --build --force-recreate frontend backend
```

### 5. Crear el tunel del frontend

En una segunda terminal independiente:

```powershell
cloudflared tunnel --url http://localhost:5173
```

Copiar la URL HTTPS mostrada, por ejemplo:

```text
https://frontend-ejemplo.trycloudflare.com
```

### 6. Completar CORS

Agregar la URL del frontend a `.env`:

```dotenv
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:5173,https://frontend-ejemplo.trycloudflare.com
```

Recrear solamente el backend:

```powershell
docker compose up -d --build --force-recreate backend
```

Actualizar el frontend no es necesario si ya se definio `VITE_ALLOWED_HOSTS=.trycloudflare.com`.

### 7. Verificar y compartir

Verificar frontend:

```powershell
curl.exe -I https://frontend-ejemplo.trycloudflare.com
```

Verificar backend:

```powershell
curl.exe https://backend-ejemplo.trycloudflare.com/api/health/
```

Verificar CORS desde el origen del frontend:

```powershell
curl.exe -I -H "Origin: https://frontend-ejemplo.trycloudflare.com" https://backend-ejemplo.trycloudflare.com/api/health/
```

La respuesta debe incluir:

```text
Access-Control-Allow-Origin: https://frontend-ejemplo.trycloudflare.com
```

Abrir y compartir:

```text
https://frontend-ejemplo.trycloudflare.com
```

## Reiniciar o consultar el despliegue

Los servicios siguen activos mientras Docker Desktop y las terminales de los tuneles permanezcan abiertos.

Consultar contenedores:

```powershell
docker compose ps
```

Consultar logs:

```powershell
docker compose logs --tail=100 frontend
docker compose logs --tail=100 backend
```

No existe una cuenta regresiva oficial para los tuneles rapidos. Para supervisar disponibilidad, revise los contenedores y haga una solicitud al frontend y al backend. Si el equipo entra en suspension o pierde conexion, el despliegue puede quedar temporalmente inaccesible.

## Detener el despliegue

En las terminales de `cloudflared`, presionar `Ctrl+C`.

Luego detener Docker Compose:

```powershell
docker compose down
```

Para mantener los datos locales de PostgreSQL al detener los contenedores, no usar `docker compose down -v`. Solo se debe conservar el volumen si se desea.

Para eliminar tambien los datos locales:

```powershell
docker compose down -v
```

Esta ultima accion elimina permanentemente la base de datos local.

## Variables utilizadas

| Variable | Uso |
|---|---|
| `VITE_API_BASE_URL` | URL publica o local del API Django |
| `VITE_ALLOWED_HOSTS` | Hosts que Vite acepta en el servidor de desarrollo |
| `DJANGO_DEBUG` | Activa o desactiva el modo debug |
| `DJANGO_SECRET_KEY` | Firma criptografica de Django |
| `DJANGO_ALLOWED_HOSTS` | Hosts admitidos por Django |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Origenes web autorizados para llamar al API |

