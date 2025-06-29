"""
Контроллер MCP (Microservice Control Plane) для управления задачами через GitHub.

Этот модуль обеспечивает интеграцию с GitHub API для оркестрации распределенных задач,
управления очередями и мониторинга выполнения.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException, status
from github import Github, GithubIntegration
from pydantic import BaseModel, Field, validator

from app.config.github_mcp import config as mcp_config
from app.core.logging import setup_logging

# Настройка логирования
logger = setup_logging(__name__)


class TaskStatus(str, Enum):
    """Статусы выполнения задач."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Приоритеты задач."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskType(str, Enum):
    """Типы поддерживаемых задач."""
    TRAIN = "train"
    PROCESS = "process"
    EVALUATE = "evaluate"
    DEPLOY = "deploy"
    CUSTOM = "custom"
    DISTRIBUTED = "distributed"


class TaskMetadata(BaseModel):
    """Метаданные задачи."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str = "system"
    priority: TaskPriority = TaskPriority.NORMAL
    retries: int = 0
    max_retries: int = 3
    timeout: int = 3600  # в секундах


class TaskResult(BaseModel):
    """Результат выполнения задачи."""
    status: TaskStatus
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    artifacts: Optional[List[str]] = None
    execution_time: Optional[float] = None  # в секундах


class Task(BaseModel):
    """Модель задачи для MCP."""
    id: str
    type: TaskType
    parameters: Dict[str, Any]
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
    result: Optional[TaskResult] = None
    dependencies: List[str] = Field(default_factory=list)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class MCPGitHubController:
    """Контроллер для управления задачами через GitHub API."""
    
    def __init__(self, config=None):
        """Инициализация контроллера."""
        self.config = config or mcp_config
        self._github = None
        self._repo = None
        self._workflow = None
    
    @property
    def github(self):
        """Ленивая инициализация клиента GitHub."""
        if self._github is None:
            # Используем GitHub App для аутентификации
            integration = GithubIntegration(
                integration_id=int(self.config.auth.app_id),
                private_key=self.config.auth.private_key
            )
            # Получаем токен установки
            access_token = integration.get_access_token(
                int(self.config.auth.installation_id)
            ).token
            self._github = Github(access_token)
        return self._github
    
    @property
    def repo(self):
        """Ленивая инициализация репозитория."""
        if self._repo is None:
            self._repo = self.github.get_repo(self.config.repo.full_name)
        return self._repo
    
    async def create_task(self, task_type: Union[str, TaskType], 
                         parameters: Dict[str, Any],
                         priority: TaskPriority = TaskPriority.NORMAL) -> Task:
        """Создает новую задачу."""
        if isinstance(task_type, str):
            task_type = TaskType(task_type.lower())
        
        task_id = f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        
        task = Task(
            id=task_id,
            type=task_type,
            parameters=parameters,
            metadata=TaskMetadata(
                priority=priority,
                created_by="api"  # TODO: Добавить информацию о пользователе
            )
        )
        
        # Сохраняем задачу в репозитории как issue
        issue_title = f"[{task_type.upper()}] {task_id}"
        issue_body = f"""
        ## Task Metadata
        
        ```json
        {task_metadata}
        ```
        
        ## Parameters
        
        ```json
        {task_parameters}
        ```
        """.format(
            task_metadata=task.metadata.json(indent=2),
            task_parameters=json.dumps(parameters, indent=2)
        )
        
        try:
            issue = self.repo.create_issue(
                title=issue_title,
                body=issue_body,
                labels=["mcp-task", f"priority-{priority.name.lower()}"]
            )
            logger.info(f"Created task {task_id} as issue #{issue.number}")
            
            # Запускаем workflow для обработки задачи
            workflow = self._get_workflow()
            if workflow:
                workflow.create_dispatch(
                    ref=self.config.repo.branch,
                    inputs={
                        "task_type": task_type.value,
                        "parameters": json.dumps(parameters)
                    }
                )
                logger.info(f"Triggered workflow for task {task_id}")
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to create task {task_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create task: {str(e)}"
            )
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """Получает статус задачи."""
        try:
            # Ищем issue по ID задачи
            issues = self.repo.get_issues(state="all", labels=["mcp-task"])
            for issue in issues:
                if task_id in issue.title:
                    # Парсим статус из комментариев
                    comments = issue.get_comments()
                    for comment in comments.reversed:
                        if "status:" in comment.body.lower():
                            status_str = comment.body.split(":")[1].strip()
                            try:
                                return TaskStatus(status_str.lower())
                            except ValueError:
                                continue
                    return TaskStatus.PENDING
            
            raise ValueError(f"Task {task_id} not found")
            
        except Exception as e:
            logger.error(f"Failed to get status for task {task_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get task status: {str(e)}"
            )
    
    async def update_task_status(self, task_id: str, status: TaskStatus, 
                               result: Optional[TaskResult] = None) -> bool:
        """Обновляет статус задачи."""
        try:
            issues = self.repo.get_issues(state="all", labels=["mcp-task"])
            for issue in issues:
                if task_id in issue.title:
                    # Добавляем комментарий со статусом
                    comment = f"Status: {status.value}\n"
                    if result:
                        comment += f"```json\n{result.json(indent=2)}\n```"
                    
                    issue.create_comment(comment)
                    
                    # Обновляем метки
                    if status == TaskStatus.COMPLETED:
                        issue.edit(state="closed")
                        issue.set_labels("mcp-task", "completed", f"priority-{issue.labels[0].name.split('-')[-1]}")
                    elif status == TaskStatus.FAILED:
                        issue.set_labels("mcp-task", "failed", f"priority-{issue.labels[0].name.split('-')[-1]}")
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update status for task {task_id}: {str(e)}")
            return False
    
    async def cancel_task(self, task_id: str) -> bool:
        """Отменяет выполнение задачи."""
        # TODO: Реализовать отмену выполнения задачи
        return await self.update_task_status(task_id, TaskStatus.CANCELLED)
    
    def _get_workflow(self):
        """Получает workflow по имени."""
        if self._workflow is None:
            workflows = self.repo.get_workflows()
            for wf in workflows:
                if wf.name == "MCP Task Controller":
                    self._workflow = wf
                    break
        return self._workflow
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверяет работоспособность MCP."""
        try:
            # Проверяем доступ к API GitHub
            rate_limit = self.github.get_rate_limit()
            
            # Проверяем доступ к репозиторию
            repo = self.repo
            
            return {
                "status": "healthy",
                "github_api": {
                    "rate_limit": {
                        "limit": rate_limit.core.limit,
                        "remaining": rate_limit.core.remaining,
                        "reset_at": rate_limit.core.reset
                    },
                    "repository": {
                        "name": repo.full_name,
                        "private": repo.private,
                        "permissions": {
                            "admin": repo.permissions.admin,
                            "push": repo.permissions.push,
                            "pull": repo.permissions.pull
                        }
                    }
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Синглтон экземпляр контроллера
controller = MCPGitHubController()


async def create_task(task_type: Union[str, TaskType], 
                    parameters: Dict[str, Any],
                    priority: TaskPriority = TaskPriority.NORMAL) -> Task:
    """Создает новую задачу."""
    return await controller.create_task(task_type, parameters, priority)


async def get_task_status(task_id: str) -> TaskStatus:
    """Получает статус задачи."""
    return await controller.get_task_status(task_id)


async def update_task_status(task_id: str, status: TaskStatus, 
                           result: Optional[TaskResult] = None) -> bool:
    """Обновляет статус задачи."""
    return await controller.update_task_status(task_id, status, result)


async def cancel_task(task_id: str) -> bool:
    """Отменяет выполнение задачи."""
    return await controller.cancel_task(task_id)


async def health_check() -> Dict[str, Any]:
    """Проверяет работоспособность MCP."""
    return await controller.health_check()


# Пример использования
if __name__ == "__main__":
    import asyncio
    
    async def example():
        # Создаем задачу
        task = await create_task(
            task_type=TaskType.PROCESS,
            parameters={"data": [1, 2, 3], "model": "test"},
            priority=TaskPriority.HIGH
        )
        print(f"Created task: {task.id}")
        
        # Проверяем статус
        status = await get_task_status(task.id)
        print(f"Task status: {status}")
        
        # Обновляем статус
        result = TaskResult(
            status=TaskStatus.COMPLETED,
            output={"result": "success"},
            metrics={"accuracy": 0.95},
            execution_time=123.45
        )
        updated = await update_task_status(task.id, TaskStatus.COMPLETED, result)
        print(f"Status updated: {updated}")
        
        # Проверяем здоровье
        health = await health_check()
        print(f"Health check: {health['status']}")
    
    asyncio.run(example())
