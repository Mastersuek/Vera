#!/bin/sh

# Проверяем доступность gRPC сервиса
python -c "\
    import grpc\
    from model_pb2_grpc import ModelServiceStub\
    from model_pb2 import ModelRequest\
    \
    channel = grpc.insecure_channel('localhost:50051')\
    stub = ModelServiceStub(channel)\
    try:\
        response = stub.GetModelInfo(ModelRequest())\
        if response.status == 'ok':\
            exit 0\
    except:\
        exit 1\
"
