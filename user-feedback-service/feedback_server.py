import grpc
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import user_feedback_pb2
import user_feedback_pb2_grpc
from grpc_interceptor import ExceptionToStatusInterceptor
from grpc_interceptor.exceptions import NotFound
from contextlib import closing

import logging  # Para o logging
from datetime import datetime

from google.protobuf.timestamp_pb2 import Timestamp  # Para gerar os timestamps ao submeter os feedbacks

# Para criar um cliente gRPC de user-service e fazer a verificação se um determinado user existe
import user_pb2
import user_pb2_grpc

# Health check gRPC
from grpc_health.v1 import health_pb2, health_pb2_grpc
from concurrent import futures

DB_URL = os.getenv("DB_URL")

# Configuracao do logger
logging.basicConfig(level=logging.DEBUG,
                  format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Cria-se um logger para o serviço
logger = logging.getLogger('user-feedback-service')

class HealthChecker(health_pb2_grpc.HealthServicer):
    def Check(self, request, context):
        try:
            # Verificação do banco de dados
            conn = psycopg2.connect(DB_URL)
            conn.close()

            channel = grpc.insecure_channel('user-service:80')
            stub = user_pb2_grpc.UserServiceStub(channel)
            
            return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)
        
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.NOT_SERVING)

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL)
        return conn
    except Exception as e:
        print(f"DB connection failed: {str(e)}")
        return False

def get_user_service_stub():
    channel = grpc.insecure_channel(
        'user-service:80',
        options=[
            ('grpc.enable_retries', 1),
            ('grpc.keepalive_timeout_ms', 10000),
            ('grpc.connect_timeout_ms', 5000)
        ]
    )
    
    stub = user_pb2_grpc.UserServiceStub(channel)
    return stub

class FeedbackService(user_feedback_pb2_grpc.FeedbackServiceServicer):
    def SubmitFeedback(self, request, context):
        username = request.feedback.username
        drug_id = request.feedback.drug_id
        text = request.feedback.feedback
        timestamp = datetime.now()

        logger.debug(f"A iniciar a submissão de feedback do utilizador {username} sobre o medicamento {drug_id}.")

        try:
            # Cria o cliente do user-service
            stub = get_user_service_stub()

            # Chama o método do user-service para verificar se o user existe
            try:
                logger.info(f"A verificar se o utilizador {username} existe no user-service.")
                user_request = user_pb2.GetUserRequest(username=username)
                user_response = stub.GetUserInfo(user_request)

                # Se o user não existe, ele retorna um erro, que você pode manipular
                if not user_response:
                    raise NotFound(f"User '{username}' não encontrado")
                logger.info(f"Utilizador {username} encontrado.")

            except grpc.RpcError as e:
                # Lida com erros de gRPC, como quando o user não é encontrado
                logger.error(f"Erro ao chamar o user-service: {e}")
                context.set_details(str(e))
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return user_feedback_pb2.SubmitFeedbackResponse(
                    message=str(e),
                    status_code=user_feedback_pb2.StatusCode.NOT_FOUND
                )

            # Se o user existir, prossegue com a submissão do feedback
            logger.debug(f"A verificar se o medicamento com ID {drug_id} existe.")
            conn = get_db_connection()
            cur = conn.cursor()

            # Verificar se o medicamento existe
            cur.execute("SELECT 1 FROM drugs WHERE id = %s", (drug_id,))
            if not cur.fetchone():
                logger.error(f"Medicamento com ID {drug_id} não encontrado.")
                raise NotFound("Medicamento não encontrado")
            logger.info(f"Medicamento com ID {drug_id} encontrado.")

            # Inserir feedback na base de dados
            logger.info(f"A inserir feedback do utilizador {username}.")
            cur.execute("""
                INSERT INTO feedback (username, drug_id, feedback, timestamp) 
                VALUES (%s, %s, %s, %s)
                """, (username, drug_id, text, timestamp))

            conn.commit()

            logger.info(f"Feedback sobre o medicamento {drug_id} do utilizador {username} registado com sucesso.") 
            return user_feedback_pb2.SubmitFeedbackResponse(
                message="Feedback registado com sucesso!",
                status_code=user_feedback_pb2.StatusCode.SUCCESS
            )

        except NotFound as e:
            logger.warning(f"Erro encontrado: {e}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return user_feedback_pb2.SubmitFeedbackResponse(
                message=str(e),
                status_code=user_feedback_pb2.StatusCode.NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Erro ao processar a inserção de feedback: {e}")
            conn.rollback()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_feedback_pb2.SubmitFeedbackResponse(
                message=str(e),
                status_code=user_feedback_pb2.StatusCode.ERROR
            )
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def GetDrugFeedback(self, request, context):
        drug_id = request.drug_id
        logger.debug(f"A iniciar o pedido para obter feedbacks do medicamento com ID {drug_id}.")

        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            logger.info(f"A consultar a base de dados para obter os feedbacks do medicamento {drug_id}.")
            cur.execute("""
                SELECT username, drug_id, feedback, timestamp 
                FROM feedback 
                WHERE drug_id = %s
                """, (drug_id,))
            results = cur.fetchall()

            if not results:
                logger.info(f"Nenhum feedback encontrado para o medicamento {drug_id}.")
                return user_feedback_pb2.DrugFeedbackResponse(feedbacks=[])

            feedbacks = []
            logger.info(f"{len(results)} feedback(s) encontrados para o medicamento {drug_id}.")
            for r in results:
                pb_timestamp = Timestamp()
                pb_timestamp.FromDatetime(r["timestamp"])
                
                feedback = user_feedback_pb2.Feedback(
                    username=r["username"],
                    drug_id=r["drug_id"],
                    feedback=r["feedback"],
                    timestamp=pb_timestamp
                )
                feedbacks.append(feedback)

            logger.info(f"Feedbacks processados com sucesso para o medicamento {drug_id}.")
            return user_feedback_pb2.DrugFeedbackResponse(feedbacks=feedbacks)

        except Exception as e:
            logger.error(f"Erro ao processar feedbacks para o medicamento {drug_id}: {e}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_feedback_pb2.DrugFeedbackResponse()
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def GetUserFeedbacks(self, request, context):
        username = request.username
        logger.debug(f"A iniciar o pedido para obter feedbacks do utilizador '{username}'.")

        try:
            # Cria o stub para comunicação com o UserService
            user_stub = get_user_service_stub()
        
            logger.info(f"A verificar se o utilizador '{username}' existe através do UserService.")
            # Verifica se o utilizador existe através da chamada do método GetUserInfo
            user_request = user_pb2.GetUserRequest(username=username)
            try:
                user_response = user_stub.GetUserInfo(user_request)  # Verifica se o utilizador existe
                logger.info(f"Utilizador '{username}' encontrado no UserService.")
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    logger.warning(f"Utilizador '{username}' não encontrado no UserService.")
                    context.set_details(f"User '{username}' não encontrado")
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    return user_feedback_pb2.DrugFeedbackResponse()  # Retorna uma resposta vazia ou erro

            # Se o user existe, continua o processo para selecionar os feedbacks
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            logger.info(f"A consultar a base de dados para feedbacks do utilizador '{username}'.")
            cur.execute("""
                SELECT username, drug_id, feedback, timestamp 
                FROM feedback 
                WHERE username = %s
                """, (username,))
            results = cur.fetchall()

            if not results:
                logger.info(f"Nenhum feedback encontrado para o utilizador {username}'.")
                return user_feedback_pb2.DrugFeedbackResponse(feedbacks=[])

            feedbacks = []
            logger.info(f"{len(results)} feedback(s) encontrados para o utilizador '{username}'.")
            for r in results:
                pb_timestamp = Timestamp()
                pb_timestamp.FromDatetime(r["timestamp"])
            
                feedback = user_feedback_pb2.Feedback(
                    username=r["username"],
                    drug_id=r["drug_id"],
                    feedback=r["feedback"],
                    timestamp=pb_timestamp
                )
                feedbacks.append(feedback)
            logger.info(f"Feedbacks processados com sucesso para o utilizador '{username}'.")
            return user_feedback_pb2.DrugFeedbackResponse(feedbacks=feedbacks)

        except Exception as e:
            logger.error(f"Erro ao obter feedbacks para o utilizador '{username}': {e}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_feedback_pb2.DrugFeedbackResponse()
    
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def DeleteUserFeedbacks(self, request, context):
        username = request.username
        logger.debug(f"A iniciar o pedido para remover todos os feedbacks do utilizador '{username}'.")

        try:
            conn = get_db_connection()
            cur = conn.cursor()

            logger.info(f"A remover os feedbacks do utilizador '{username}' na base de dados.")
            cur.execute("DELETE FROM feedback WHERE username = %s", (username,))
            conn.commit()

            logger.info(f"Todos os feedbacks do utilizador '{username}' foram removidos com sucesso.")

            return user_feedback_pb2.Response(
                message=f"Todos os feedbacks do utilizador {username} foram removidos",
                status_code=user_feedback_pb2.StatusCode.SUCCESS
            )

        except Exception as e:
            logger.error(f"Erro ao remover os feedbacks do utilizador '{username}': {e}")
            conn.rollback()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_feedback_pb2.Response(
                message=str(e),
                status_code=user_feedback_pb2.StatusCode.ERROR
            )
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def UpdateFeedback(self, request, context):
        username = request.username
        drug_id = request.drug_id
        new_feedback = request.new_feedback
        timestamp = datetime.now()

        logger.debug(f"A iniciar a atualização do feedback feito pelo utilizador '{username}' do medicamento '{drug_id}'.")

        try:
            # Cria o stub para comunicação com o UserService
            user_stub = get_user_service_stub()
        
            # Verifica se o user existe através da chamada ao método GetUserInfo
            user_request = user_pb2.GetUserRequest(username=username)
            try:
                user_response = user_stub.GetUserInfo(user_request)  # Verifica se o user existe
                logger.info(f"Utilizador '{username}' encontrado no UserService.")
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    logger.error(f"Utilizador '{username}' não encontrado no UserService.")
                    context.set_details(f"User '{username}' não encontrado")
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    return user_feedback_pb2.Response()  # Retorna uma resposta vazia ou erro

            conn = get_db_connection()
            cur = conn.cursor()

            # Verificar se o feedback existe
            cur.execute("""
                SELECT 1 FROM feedback 
                WHERE username = %s AND drug_id = %s
                """, (username, drug_id))
            if not cur.fetchone():
                logger.warning(f"Feedback não encontrado feito pelo utilizador '{username}' sobre o medicamento '{drug_id}'.")
                raise NotFound("Feedback não encontrado")

            logger.info(f"Feedback encontrado, a proceder à atualização.")
            # Atualizar o feedback
            cur.execute("""
                UPDATE feedback 
                SET feedback = %s, timestamp = %s
                WHERE username = %s AND drug_id = %s
                """, (new_feedback, timestamp, username, drug_id))
            conn.commit()

            pb_timestamp = Timestamp()
            pb_timestamp.FromDatetime(timestamp)

            logger.info(f"Feedback do utilizador '{username}' sobre o medicamento '{drug_id}' atualizado com sucesso.")

            return user_feedback_pb2.Response(
                message="Feedback atualizado com sucesso",
                status_code=user_feedback_pb2.StatusCode.SUCCESS
            )

        except Exception as e:
            logger.error(f"Erro ao atualizar o feedback do utilizador '{username}' para o medicamento '{drug_id}': {e}")
            conn.rollback()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_feedback_pb2.Response(
                message=str(e),
                status_code=user_feedback_pb2.StatusCode.ERROR
            )
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def DeleteFeedback(self, request, context):
        username = request.username
        drug_id = request.drug_id
        pb_timestamp = request.timestamp
        timestamp = pb_timestamp.ToDatetime()
        logger.debug(f"A eliminar feedback do utilizador '{username}' relativo ao medicamento '{drug_id}' com timestamp '{timestamp}'.")

        try:
            # Cria o stub para comunicação com o UserService
            user_stub = get_user_service_stub()

            # Verifica se o user existe através da chamada do método GetUserInfo
            user_request = user_pb2.GetUserRequest(username=username)
            try:
                user_response = user_stub.GetUserInfo(user_request)  # Verifica se o user existe
                logger.info(f"Utilizador '{username}' encontrado no UserService.")
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    logger.error(f"Utilizador '{username}' não encontrado no UserService.")
                    context.set_details(f"User '{username}' não encontrado")
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    return user_feedback_pb2.Response()  # Retorna uma resposta vazia ou erro

            conn = get_db_connection()
            cur = conn.cursor()

            # Verificar se o feedback existe com o timestamp
            cur.execute("""
                SELECT 1 FROM feedback 
                WHERE username = %s AND drug_id = %s AND timestamp = %s
                """, (username, drug_id, timestamp))

            if not cur.fetchone():
                logger.warning(f"Feedback não encontrado para o utilizador '{username}' sobre o medicamento '{drug_id}' com timestamp '{timestamp}'.")
                raise NotFound("Feedback não encontrado")

            logger.info(f"Feedback encontrado, a efetuar a com a removoção.")
            # Excluir o feedback
            cur.execute("""
                DELETE FROM feedback 
                WHERE username = %s AND drug_id = %s AND timestamp = %s
                """, (username, drug_id, timestamp))
            conn.commit()

            logger.info(f"Feedback removido com sucesso para o utilizador '{username}' sobre o medicamento '{drug_id}' com timestamp '{timestamp}'.")
            return user_feedback_pb2.Response(
                message="Feedback removido com sucesso",
                status_code=user_feedback_pb2.StatusCode.SUCCESS
            )

        except Exception as e:
            logger.error(f"Erro ao remover o feedback do utilizador '{username}' sobre o medicamento '{drug_id}' com timestamp '{timestamp}': {e}")
            conn.rollback()
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_feedback_pb2.Response(
                message=str(e),
                status_code=user_feedback_pb2.StatusCode.ERROR
            )
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

    def ListAllFeedbacks(self, request, context):
        logger.debug("A devolver todos os todos os feedbacks.")
        try:
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)

            logger.info("A verificar todos os feedbacks na base de dados.")
            cur.execute("SELECT username, drug_id, feedback, timestamp FROM feedback")
            results = cur.fetchall()

            if not results:
                logger.info("Nenhum feedback encontrado.")
                return user_feedback_pb2.ListAllFeedbacksResponse(feedbacks=[])

            logger.info(f"{len(results)} feedback(s) encontrado(s).")

            feedbacks = []
            for r in results:
                pb_timestamp = Timestamp()
                pb_timestamp.FromDatetime(r["timestamp"])
                
                feedback = user_feedback_pb2.Feedback(
                    username=r["username"],
                    drug_id=r["drug_id"],
                    feedback=r["feedback"],
                    timestamp=pb_timestamp
                )
                feedbacks.append(feedback)

            logger.info(f"{len(feedbacks)} feedback(s) processado(s) e retornado(s) com sucesso.")
            return user_feedback_pb2.ListAllFeedbacksResponse(feedbacks=feedbacks)

        except Exception as e:
            logger.error(f"Erro ao procurar todos os feedbacks: {e}")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            return user_feedback_pb2.ListAllFeedbacksResponse()
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

def test_db_connection():
    """Testa a conexão com o banco de dados para readiness check"""
    logger.debug("A iniciar o teste de conexão com a base de dados.")
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("Conexão com a base de dados bem sucedida.")
        return True
    except Exception as e:
        logger.error(f"Falha na conexão com a base de dados: {e}")
        return False

def serve():
    interceptors = [ExceptionToStatusInterceptor()]
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), interceptors=interceptors)
    
    # Adiciona os serviços
    user_feedback_pb2_grpc.add_FeedbackServiceServicer_to_server(FeedbackService(), server)
    health_pb2_grpc.add_HealthServicer_to_server(HealthChecker(), server)
    
    server.add_insecure_port('[::]:50053')
    server.start()

    logger.info("Feedback gRPC server running on port 50053")
    
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
