from concurrent import futures
import grpc
import psycopg2
import os
import bcrypt
from datetime import datetime

import user_pb2
import user_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound

from grpc_health.v1 import health_pb2, health_pb2_grpc

import logging # Para o logging

DB_URL = os.getenv("DB_URL")

# Configuração do logger
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Criação do logger para o serviço
logger = logging.getLogger('user-service')

class HealthServicer(health_pb2_grpc.HealthServicer):
    def Check(self, request, context):
        logger.info("Health check requested for service: %s", request.service)

        try:
            # Verifica se a conexão com o base de dados está a funcionar
            conn = psycopg2.connect(DB_URL)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")  # Testa a conexão com uma consulta simples
            cursor.close()
            conn.close()

            logger.info("Database connection successful.")

            # Se a verificação for bem-sucedida, retorna SERVING
            return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)

        except psycopg2.OperationalError as e:
            # Em caso de erro na conexão com a base de dados
            logger.error("Database connection failed: %s", str(e))
            return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.NOT_SERVING)

        except Exception as e:
            # Caso ocorram outros tipos de erro
            logger.error("Health check failed: %s", str(e))
            return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.NOT_SERVING)

class UserService(user_pb2_grpc.UserServiceServicer):
    def RegisterUser(self, request, context):
        user = request.user
        username = user.username
        email = user.email
        password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        logger.debug(f"A iniciar o registo do utilizador {username} com email {email}.")

        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()

            # Verifica se user ou email já existem
            logger.info(f"A verificar se o utilizador '{username}' ou o email '{email}' já existem na base de dados.")
            cur.execute("SELECT 1 FROM users WHERE username = %s OR email = %s", (username, email))
            if cur.fetchone():
                logger.warning(f"Erro: Username '{username}' ou email '{email}' já existem na base de dados.")
                raise NotFound("Username ou email já existem")

            # Insere novo user com hash da password
            logger.info(f"A inserir novo utilizador {username} na base de dados.")
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, password)
            )
            conn.commit()
            
            logger.info(f"Utilizador {username} registado com sucesso.")
            return user_pb2.UserOperationResponse(
                success=True,
                message="Utilizador registado com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao registar utilizador {username}: {str(e)}")
            conn.rollback()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_pb2.UserOperationResponse(
                success=False,
                message=f"Erro ao registar utilizador: {str(e)}"
            )
        finally:
            if 'cur' in locals(): cur.close()
            if 'conn' in locals(): conn.close()

    def UpdateUser(self, request, context):
        username = request.username
        new_email = request.new_email
        new_password = request.new_password

        logger.debug(f"A efetuar atualização das informações do utilizador {username}. Novo email: {new_email}, nova senha: {'******' if new_password else 'não fornecida'}.")

        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()

            # Verifica se o user existe
            logger.info(f"A verificar se o utilizador '{username}' existe.")
            cur.execute("SELECT 1 FROM users WHERE username = %s", (username,))
            if not cur.fetchone():
                logger.warning(f"Utilizador '{username}' não encontrado.")
                raise NotFound("Utilizador não encontrado")

            # Prepara os campos para atualização
            updates = []
            params = []
            
            if new_email:
                # Verifica se o novo email já está em uso
                logger.info(f"A verificar se o novo email '{new_email}' está em uso por outro utilizador.")
                cur.execute("SELECT 1 FROM users WHERE email = %s AND username != %s", (new_email, username))
                if cur.fetchone():
                    logger.warning(f"Email '{new_email}' já está em uso por outro utilizador.")
                    raise NotFound("Email já está em uso por outro utilizador")
                updates.append("email = %s")
                params.append(new_email)
            
            if new_password:
                password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                updates.append("password = %s")
                params.append(password)
            
            if not updates:
                logger.info("Nenhum dado fornecido para atualização.")
                return user_pb2.UserOperationResponse(
                    success=False,
                    message="Nenhum dado para atualizar"
                )
            
            # Adiciona campo de atualização e completa a query
            params.append(username)
            query = f"UPDATE users SET {', '.join(updates)} WHERE username = %s"
            logger.info(f"A atualizar as informações do utilizador '{username}' com os seguintes dados: {', '.join(updates)}.")
            cur.execute(query, params)
            conn.commit()
            
            logger.info(f"Dados do utilizador '{username}' atualizados com sucesso.")
            return user_pb2.UserOperationResponse(
                success=True,
                message="Utilizador atualizado com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao atualizar os dados do utilizador '{username}': {str(e)}")
            conn.rollback()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_pb2.UserOperationResponse(
                success=False,
                message=f"Erro ao atualizar os dados do utilizador: {str(e)}"
            )
        finally:
            if 'cur' in locals(): cur.close()
            if 'conn' in locals(): conn.close()

    def DeleteUser(self, request, context):
        username = request.username

        logger.debug(f"A iniciar a remoção do utilizador '{username}'.")

        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()

            logger.info(f"A tentar remover o utilizador '{username}'.")
            cur.execute("DELETE FROM users WHERE username = %s", (username,))
            conn.commit()
            
            if cur.rowcount == 0:
                logger.warning(f"Utilizador '{username}' não encontrado para remoção.")
                raise NotFound("Utilizador não encontrado")
            
            logger.info(f"Utilizador '{username}' removido da base dados com sucesso.")
            return user_pb2.UserOperationResponse(
                success=True,
                message="Utilizador eliminado com sucesso"
            )

        except Exception as e:
            logger.error(f"Erro ao eliminar utilizador '{username}': {str(e)}")
            conn.rollback()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_pb2.UserOperationResponse(
                success=False,
                message=f"Erro ao eliminar utilizador: {str(e)}"
            )
        finally:
            if 'cur' in locals(): cur.close()
            if 'conn' in locals(): conn.close()

    def GetUserInfo(self, request, context):
        username = request.username

        logger.debug(f"A preparar a recolha de informações do utilizador '{username}'.")

        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()
            logger.info(f"A recolher as informações do utilizador '{username}'.") 
            cur.execute(
                "SELECT username, email FROM users WHERE username = %s",
                (username,)
            )
            result = cur.fetchone()
            
            if not result:
                logger.warning(f"Utilizador '{username}' não encontrado.")
                raise NotFound("Utilizador não encontrado")
            
            logger.info(f"Informações do utilizador '{username}' recolhidas com sucesso.")
            return user_pb2.UserResponse(
                username=result[0],
                email=result[1]
            )

        except Exception as e:
            logger.error(f"Erro ao recolher as informações do utilizador '{username}': {str(e)}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_pb2.UserResponse()
        finally:
            if 'cur' in locals(): cur.close()
            if 'conn' in locals(): conn.close()

def test_db_connection():
    """Testa a ligacao com a base de dados para readiness check"""
    logger.debug("A iniciar o teste de conexão com a base de dados.")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.close()
        logger.info("Conexão com a base de dados bem sucedida.")
        return True
    except Exception as e:
        logger.error(f"Falha na conexão com a base de dados: {e}")
        return False

def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors)
    
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)
    
    
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.info("Feedback gRPC server running on port 50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
