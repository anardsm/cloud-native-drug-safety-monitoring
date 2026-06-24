import grpc
import user_pb2
import user_pb2_grpc
from getpass import getpass  

LB_IP = "34.90.142.237"
LB_PORT = 80

def print_menu():
    print("\n=== Menu do Cliente ===")
    print("1. Registar novo user")
    print("2. Atualizar user (email/password)")
    print("3. Obter informações do user")
    print("4. Eliminar user")
    print("5. Sair")
    return input("Escolha uma opção: ")

def register_user(stub):
    print("\n--- Registar novo user ---")
    username = input("Username: ")
    email = input("Email: ")
    password = getpass("Password: ")
    
    user = user_pb2.User(username=username, email=email, password=password)
    request = user_pb2.RegisterUserRequest(user=user)
    
    response = stub.RegisterUser(request)
   
    print(f"\nResposta: {response.message} (Sucesso: {response.success})")

def update_user(stub):
    print("\n--- Atualizar user ---")
    username = input("Username do user a atualizar: ")
    
    print("Deixe em branco para manter o valor atual")
    new_email = input("Novo email: ") or None
    new_password = getpass("Nova password: ") or None
    
    request = user_pb2.UpdateUserRequest(
        username=username,
        new_email=new_email,
        new_password=new_password
    )
    
    response = stub.UpdateUser(request)
    print(f"\nResposta: {response.message} (Sucesso: {response.success})")

def get_user_info(stub):
    print("\n--- Obter informações do user ---")
    username = input("Username: ")
    
    request = user_pb2.DeleteUserRequest(username=username)  
    response = stub.GetUserInfo(request)
    
    if response.username:
        print(f"\nInformações do user:")
        print(f"Username: {response.username}")
        print(f"Email: {response.email}")
    else:
        print("\nUser não encontrado")

def delete_user(stub):
    print("\n--- Eliminar user ---")
    username = input("Username do user a eliminar: ")
    
    request = user_pb2.DeleteUserRequest(username=username)
    response = stub.DeleteUser(request)
    
    print(f"\nResposta: {response.message} (Sucesso: {response.success})")

def run():
    
    channel = grpc.insecure_channel(f'{LB_IP}:{LB_PORT}')
    
    try:
   
        grpc.channel_ready_future(channel).result(timeout=5)
        print("Conexão com o servidor estabelecida com sucesso!")
    except grpc.FutureTimeoutError:
        print("Erro: Não foi possível conectar ao servidor")
        return
    
    stub = user_pb2_grpc.UserServiceStub(channel)
    
    while True:
        choice = print_menu()
        
        try:
            if choice == "1":
                register_user(stub)
            elif choice == "2":
                update_user(stub)
            elif choice == "3":
                get_user_info(stub)
            elif choice == "4":
                delete_user(stub)
            elif choice == "5":
                print("A sair...")
                break
            else:
                print("Opção inválida, tente de novo")
        except grpc.RpcError as e:
            print(f"\nErro na comunicação com o servidor: {e.code()}: {e.details()}")
        except Exception as e:
            print(f"\nErro inesperado: {str(e)}")

if __name__ == "__main__":
    run()
