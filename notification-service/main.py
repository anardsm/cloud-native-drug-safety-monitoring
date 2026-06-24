import os
import connexion
from app import database
from app.models import Notification

# Cria app Connexion
app = connexion.App(__name__, specification_dir="openapi/")
app.add_api("openapi.yaml")

# Acede ao app Flask interno (caso precises de adicionar configs ou usar Gunicorn)
application = app.app

# Inicializa a base de dados apenas quando correr localmente
if __name__ == "__main__":
    database.Base.metadata.create_all(bind=database.engine)
    application.run(host="0.0.0.0", port=8001, debug=True)
