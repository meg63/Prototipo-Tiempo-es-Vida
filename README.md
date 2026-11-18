# Prototipo-Tiempo-es-Vida

Para ejecutar, abrir Docker Desktop 
Luego abrir el repositorio en Visual Studio y ejecutar
copy .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py cargar_recomendaciones
docker compose exec backend python manage.py createsuperuser

Luego abrir la plataforma en
http://localhost:5173