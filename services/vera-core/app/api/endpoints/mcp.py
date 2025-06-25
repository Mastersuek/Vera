"""
API эндпоинты для управления задачами через MCP (Microservice Control Plane).

Этот модуль предоставляет REST API для создания, мониторинга и управления задачами,
используя GitHub в качестве бэкенда для оркестрации.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from app.mcp.controller import (
    create_task,
    get_task_status,
    update_task_status,
    cancel_task,
    health_check,
    Task,
    TaskStatus,
    TaskType,
    TaskPriority,
    TaskResult
)
from app.core.security import get_current_user
from app.schemas.user import User

router = APIRouter(prefix="/mcp", tags=["MCP"])


class TaskCreate(BaseModel):
    """Модель для создания новой задачи."""
    task_type: str = Field(..., description="Тип задачи (train, process, evaluate, deploy, custom, distributed)")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Параметры задачи")
    priority: str = Field("normal", description="Приоритет задачи (low, normal, high, critical)")


class TaskStatusResponse(BaseModel):
    """Модель ответа со статусом задачи."""
    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}


class HealthCheckResponse(BaseModel):
    """Модель ответа для проверки работоспособности."""
    status: str
    details: Dict[str, Any]
    timestamp: str


@router.post("/tasks/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_new_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Создает новую задачу.
    
    - **task_type**: Тип задачи (train, process, evaluate, deploy, custom, distributed)
    - **parameters**: Параметры задачи в формате JSON
    - **priority**: Приоритет задачи (low, normal, high, critical)
    """
    try:
        # Преобразуем приоритет
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL
        }
        priority = priority_map.get(task_data.priority.lower(), TaskPriority.NORMAL)
        
        # Добавляем информацию о пользователе в параметры
        task_data.parameters["_created_by"] = {
            "user_id": str(current_user.id),
            "username": current_user.username,
            "email": current_user.email
        }
        
        # Создаем задачу
        task = await create_task(
            task_type=task_data.task_type,
            parameters=task_data.parameters,
            priority=priority
        )
        
        return task
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании задачи: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Получает статус задачи по её идентификатору.
    
    - **task_id**: Уникальный идентификатор задачи
    """
    try:
        status = await get_task_status(task_id)
        return {
            "task_id": task_id,
            "status": status.value,
            "metadata": {}
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении статуса задачи: {str(e)}"
        )


@router.post("/tasks/{task_id}/cancel", response_model=TaskStatusResponse)
async def cancel_existing_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Отменяет выполнение задачи.
    
    - **task_id**: Уникальный идентификатор задачи для отмены
    """
    try:
        success = await cancel_task(task_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Задача {task_id} не найдена или уже завершена"
            )
            
        return {
            "task_id": task_id,
            "status": "cancelled",
            "metadata": {}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при отмене задачи: {str(e)}"
        )


@router.get("/health", response_model=HealthCheckResponse)
async def check_health():
    """
    Проверяет работоспособность MCP и интеграции с GitHub.
    
    Возвращает текущий статус системы, включая информацию о лимитах API GitHub.
    """
    try:
        health_data = await health_check()
        return {
            "status": health_data["status"],
            "details": health_data,
            "timestamp": health_data["timestamp"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/task-types/", response_model=List[Dict[str, str]])
async def list_available_task_types():
    """
    Возвращает список доступных типов задач.
    
    Каждый тип задачи содержит идентификатор и описание.
    """
    return [
        {
            "id": "train",
            "description": "Обучение модели машинного обучения"
        },
        {
            "id": "process",
            "description": "Обработка данных"
        },
        {
            "id": "evaluate",
            "description": "Оценка качества модели"
        },
        {
            "id": "deploy",
            "description": "Развертывание модели"
        },
        {
            "id": "distributed",
            "description": "Распределенная обработка"
        },
        {
            "id": "custom",
            "description": "Пользовательская задача"
        }
    ]


# Webhook для обработки событий от GitHub
@router.post("/webhooks/github")
async def github_webhook(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Webhook для приема событий от GitHub.
    
    Используется для обновления статусов задач на основе событий GitHub Actions.
    """
    try:
        event_type = request.headers.get("X-GitHub-Event")
        
        if event_type == "workflow_run":
            # Обработка событий workflow_run
            workflow_run = payload["workflow_run"]
            workflow_name = workflow_run["name"]
            status = workflow_run["status"]
            conclusion = workflow_run.get("conclusion")
            
            # Извлекаем ID задачи из имени workflow
            task_id = None
            if "MCP Task" in workflow_name:
                # Формат: "MCP Task: {task_id}"
                task_id = workflow_name.split(":")[1].strip()
            
            if task_id:
                # Обновляем статус задачи в фоне
                background_tasks.add_task(
                    update_task_from_workflow,
                    task_id=task_id,
                    status=status,
                    conclusion=conclusion,
                    workflow_run=workflow_run
                )
        
        return {"status": "received"}
        
    except Exception as e:
        logger.error(f"Error processing GitHub webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


async def update_task_from_workflow(
    task_id: str,
    status: str,
    conclusion: Optional[str],
    workflow_run: Dict[str, Any]
):
    """Обновляет статус задачи на основе события workflow_run."""
    try:
        # Преобразуем статус GitHub в наш формат
        task_status = None
        if status == "completed":
            if conclusion == "success":
                task_status = TaskStatus.COMPLETED
            else:
                task_status = TaskStatus.FAILED
        elif status == "in_progress":
            task_status = TaskStatus.RUNNING
        elif status in ["queued", "waiting"]:
            task_status = TaskStatus.PENDING
        
        if task_status:
            result = TaskResult(
                status=task_status,
                output={
                    "workflow_run_id": workflow_run["id"],
                    "html_url": workflow_run["html_url"],
                    "run_number": workflow_run["run_number"],
                    "event": workflow_run["event"],
                    "status": status,
                    "conclusion": conclusion
                }
            )
            
            await update_task_status(task_id, task_status, result)
            
    except Exception as e:
        logger.error(f"Error updating task {task_id} from workflow: {str(e)}")
        # Не прокидываем исключение, чтобы не ломать обработку вебхука
