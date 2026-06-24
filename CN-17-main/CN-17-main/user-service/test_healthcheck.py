import grpc
from grpc_health.v1 import health_pb2, health_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = health_pb2_grpc.HealthStub(channel)

response = stub.Check(health_pb2.HealthCheckRequest(service="user.UserService"))
print(f"Status: {health_pb2.HealthCheckResponse.ServingStatus.Name(response.status)}")