import grpc
import user_feedback_pb2
import user_feedback_pb2_grpc
from google.protobuf import empty_pb2
from google.protobuf.timestamp_pb2 import Timestamp
from datetime import datetime

LB_IP = "34.13.253.133"
LB_PORT = 80            

def print_feedback(feedback):
    timestamp = datetime.fromtimestamp(feedback.timestamp.seconds + feedback.timestamp.nanos/1e9)
    print(f"User: {feedback.username}, Drug ID: {feedback.drug_id}")
    print(f"Feedback: {feedback.feedback}")
    print(f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 40)

def run():
    # Configuração do canal para o LoadBalancer
    channel = grpc.insecure_channel(f'{LB_IP}:{LB_PORT}')
    
    try:
        # Testa a conexão
        grpc.channel_ready_future(channel).result(timeout=30)
        print("Conexão com o servidor estabelecida com sucesso!")
    except grpc.FutureTimeoutError:
        print("Erro: Não foi possível conectar ao servidor")
        return
    
    stub = user_feedback_pb2_grpc.FeedbackServiceStub(channel)
        
    print("=== TESTAR OPERAÇÕES DE FEEDBACK ===")
    
    # 1. Submeter feedback inicial
    print("\n1. Submeter feedback inicial")
    feedback = user_feedback_pb2.Feedback(
        username="ana", 
        drug_id=1, 
        feedback="Muito eficaz!"
    )
    response = stub.SubmitFeedback(user_feedback_pb2.SubmitFeedbackRequest(feedback=feedback))
    print(f"Resposta: {response.message} (status {response.status_code})")

    # 2. Submeter segundo feedback (mesmo user e medicamento)
    print("\n2. Submeter segundo feedback (mesmo user e medicamento)")
    feedback = user_feedback_pb2.Feedback(
        username="ana", 
        drug_id=1, 
        feedback="Sem efeitos colaterais"
    )
    response = stub.SubmitFeedback(user_feedback_pb2.SubmitFeedbackRequest(feedback=feedback))
    print(f"Resposta: {response.message} (status {response.status_code})")

    # 3. Submeter feedback para outro user
    print("\n3. Submeter feedback para outro user")
    feedback = user_feedback_pb2.Feedback(
        username="joao", 
        drug_id=1, 
        feedback="Funcionou parcialmente"
    )
    response = stub.SubmitFeedback(user_feedback_pb2.SubmitFeedbackRequest(feedback=feedback))
    print(f"Resposta: {response.message} (status {response.status_code})")

    # 4. Obter feedbacks para um medicamento
    print("\n4. Obter feedbacks para o medicamento 1")
    drug_feedbacks = stub.GetDrugFeedback(user_feedback_pb2.DrugFeedbackRequest(drug_id=1))
    print(f"Total de feedbacks encontrados: {len(drug_feedbacks.feedbacks)}")
    for fb in drug_feedbacks.feedbacks:
        print_feedback(fb)

    # 5. Obter feedbacks de um user específico
    print("\n5. Obter feedbacks da user 'ana'")
    user_feedbacks = stub.GetUserFeedbacks(user_feedback_pb2.UserFeedbackRequest(username="ana"))
    print(f"Total de feedbacks encontrados: {len(user_feedbacks.feedbacks)}")
    for fb in user_feedbacks.feedbacks:
        print_feedback(fb)

    # 6. Atualizar um feedback específico
    print("\n6. Atualizar feedback da ana para o medicamento 1")
    update_response = stub.UpdateFeedback(user_feedback_pb2.UpdateFeedbackRequest(
        username="ana",
        drug_id=1,
        new_feedback="Muito eficaz mesmo! Sem efeitos colaterais."
    ))
    print(f"Resposta: {update_response.message} (status {update_response.status_code})")

    # Verificar atualização
    print("\nVerificando atualização:")
    user_feedbacks = stub.GetUserFeedbacks(user_feedback_pb2.UserFeedbackRequest(username="ana"))
    for fb in user_feedbacks.feedbacks:
        print_feedback(fb)

    # 7. Listar todos os feedbacks do sistema
    print("\n7. Listar todos os feedbacks do sistema")
    all_feedbacks = stub.ListAllFeedbacks(empty_pb2.Empty())
    print(f"Total de feedbacks no sistema: {len(all_feedbacks.feedbacks)}")
    for fb in all_feedbacks.feedbacks:
        print_feedback(fb)

    # 8. Apagar um feedback específico
    print("\n8. Apagar feedback do joao para o medicamento 1")
    delete_response = stub.DeleteFeedback(user_feedback_pb2.DeleteFeedbackRequest(
        username="joao",
        drug_id=1
    ))
    print(f"Resposta: {delete_response.message} (status {delete_response.status_code})")

    # 9. Apagar todos os feedbacks de um user
    print("\n9. Apagar todos os feedbacks da ana")
    delete_all_response = stub.DeleteUserFeedbacks(user_feedback_pb2.UserFeedbackRequest(username="ana"))
    print(f"Resposta: {delete_all_response.message} (status {delete_all_response.status_code})")

    # Verificar estado final
    print("\nEstado final do sistema:")
    all_feedbacks = stub.ListAllFeedbacks(empty_pb2.Empty())
    print(f"Total de feedbacks no sistema: {len(all_feedbacks.feedbacks)}")
    for fb in all_feedbacks.feedbacks:
        print_feedback(fb)

if __name__ == "__main__":
    run()
