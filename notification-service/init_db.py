from app import database
from app.models import Notification

database.Base.metadata.create_all(bind=database.engine)
print("✅ Tabela 'notifications' criada com sucesso!")
