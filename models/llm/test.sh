#!/bin/sh

# Тестирование модели
python -c "\
    import grpc\
    from model_pb2_grpc import ModelServiceStub\
    from model_pb2 import ModelRequest\
    import time\
    import sys\
    \
    channel = grpc.insecure_channel('localhost:50051')\
    stub = ModelServiceStub(channel)\
    \
    try:\
        # Тест 1: Базовый запрос\
        print('Test 1: Basic request')\
        request = ModelRequest(prompt='Привет, как дела?')\
        response = stub.Generate(request)\
        print(f'Response: {response.text}')\
        \
        # Тест 2: Длинный запрос\
        print('\nTest 2: Long request')\
        long_prompt = 'Напиши подробный рассказ о приключениях в лесу'\
        request = ModelRequest(prompt=long_prompt, max_length=1024)\
        start_time = time.time()\
        response = stub.Generate(request)\
        duration = time.time() - start_time\
        print(f'Response length: {len(response.text)} chars')\
        print(f'Generation time: {duration:.2f} seconds')\
        \
        # Тест 3: Проверка параметров\
        print('\nTest 3: Parameters test')\
        request = ModelRequest(prompt='Сгенерируй стихотворение', temperature=0.9, top_p=0.8)\
        response = stub.Generate(request)\
        print(f'Generated poem: {response.text}')\
        \
        print('\nAll tests passed successfully!')\
        exit 0\
        \
    except Exception as e:\
        print(f'Error: {str(e)}', file=sys.stderr)\
        exit 1\
"
