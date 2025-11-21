"""
Сервис для запуска ML-скриптов через API.
Обеспечивает асинхронный запуск и мониторинг выполнения скриптов.
"""
import os
import sys
import subprocess
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path
from enum import Enum

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScriptStatus(Enum):
    """Статусы выполнения скрипта"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MLScriptService:
    """Сервис для управления выполнением ML-скриптов"""
    
    def __init__(self, scripts_directory: str = None):
        """
        Инициализация сервиса
        
        Args:
            scripts_directory: Путь к директории со скриптами (по умолчанию ../scripts или /scripts в Docker)
        """
        if scripts_directory is None:
            # Проверяем, работаем ли в Docker (путь /scripts существует)
            docker_scripts_path = Path("/scripts")
            if docker_scripts_path.exists():
                scripts_directory = str(docker_scripts_path)
            else:
                # Определяем путь к scripts относительно backend
                backend_dir = Path(__file__).parent.parent
                scripts_directory = str(backend_dir.parent / "scripts")
        
        self.scripts_directory = Path(scripts_directory).resolve()
        self.running_processes: Dict[str, subprocess.Popen] = {}
        self.script_status: Dict[str, Dict] = {}
        
        # Проверяем существование директории
        if not self.scripts_directory.exists():
            raise ValueError(f"Директория скриптов не найдена: {self.scripts_directory}")
    
    def _get_script_path(self, script_name: str) -> Path:
        """Получает полный путь к скрипту"""
        script_path = self.scripts_directory / script_name
        if not script_path.exists():
            raise FileNotFoundError(f"Скрипт не найден: {script_path}")
        return script_path
    
    def _validate_script(self, script_name: str) -> bool:
        """Проверяет существование и доступность скрипта"""
        try:
            script_path = self._get_script_path(script_name)
            return script_path.exists() and script_path.is_file()
        except Exception as e:
            logger.error(f"Ошибка валидации скрипта {script_name}: {e}")
            return False
    
    async def run_script(
        self,
        script_name: str,
        args: List[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Dict:
        """
        Запускает ML-скрипт асинхронно
        
        Args:
            script_name: Имя скрипта (например, 'data_collector.py')
            args: Дополнительные аргументы для скрипта
            timeout: Таймаут выполнения в секундах (None = без таймаута)
            env: Дополнительные переменные окружения
        
        Returns:
            Словарь с результатом выполнения
        """
        if args is None:
            args = []
        
        # Валидация скрипта
        if not self._validate_script(script_name):
            return {
                "status": ScriptStatus.FAILED.value,
                "error": f"Скрипт {script_name} не найден или недоступен",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Проверка, не запущен ли уже этот скрипт
        if script_name in self.running_processes:
            return {
                "status": ScriptStatus.RUNNING.value,
                "message": f"Скрипт {script_name} уже выполняется",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        script_path = self._get_script_path(script_name)
        
        # Подготовка переменных окружения
        script_env = os.environ.copy()
        if env:
            script_env.update(env)
        
        # Подготовка команды
        python_cmd = sys.executable
        cmd = [python_cmd, str(script_path)] + args
        
        try:
            # Обновляем статус
            self.script_status[script_name] = {
                "status": ScriptStatus.RUNNING.value,
                "started_at": datetime.utcnow().isoformat(),
                "command": " ".join(cmd)
            }
            
            logger.info(f"Запуск скрипта: {' '.join(cmd)}")
            
            # Запускаем процесс
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.scripts_directory),
                env=script_env
            )
            
            self.running_processes[script_name] = process
            
            # Ждем завершения с таймаутом
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                # Декодируем вывод
                stdout_text = stdout.decode('utf-8', errors='ignore') if stdout else ""
                stderr_text = stderr.decode('utf-8', errors='ignore') if stderr else ""
                
                # Проверяем код возврата
                if process.returncode == 0:
                    status = ScriptStatus.COMPLETED.value
                    error = None
                else:
                    status = ScriptStatus.FAILED.value
                    error = stderr_text or f"Скрипт завершился с кодом {process.returncode}"
                
                # Обновляем статус
                self.script_status[script_name].update({
                    "status": status,
                    "completed_at": datetime.utcnow().isoformat(),
                    "return_code": process.returncode,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "error": error
                })
                
                result = {
                    "status": status,
                    "script_name": script_name,
                    "return_code": process.returncode,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "started_at": self.script_status[script_name]["started_at"],
                    "completed_at": self.script_status[script_name]["completed_at"],
                }
                
                if error:
                    result["error"] = error
                
            except asyncio.TimeoutError:
                # Таймаут - убиваем процесс
                process.kill()
                await process.wait()
                
                status = ScriptStatus.FAILED.value
                error = f"Таймаут выполнения ({timeout} секунд)"
                
                self.script_status[script_name].update({
                    "status": status,
                    "completed_at": datetime.utcnow().isoformat(),
                    "error": error
                })
                
                result = {
                    "status": status,
                    "script_name": script_name,
                    "error": error,
                    "started_at": self.script_status[script_name]["started_at"],
                    "completed_at": self.script_status[script_name]["completed_at"],
                }
            
            finally:
                # Удаляем из активных процессов
                if script_name in self.running_processes:
                    del self.running_processes[script_name]
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при запуске скрипта {script_name}: {e}", exc_info=True)
            
            status = ScriptStatus.FAILED.value
            error = str(e)
            
            self.script_status[script_name] = {
                "status": status,
                "error": error,
                "started_at": datetime.utcnow().isoformat(),
                "completed_at": datetime.utcnow().isoformat()
            }
            
            if script_name in self.running_processes:
                del self.running_processes[script_name]
            
            return {
                "status": status,
                "script_name": script_name,
                "error": error,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_script_status(self, script_name: str) -> Optional[Dict]:
        """Получает статус выполнения скрипта"""
        return self.script_status.get(script_name)
    
    def get_all_statuses(self) -> Dict[str, Dict]:
        """Получает статусы всех скриптов"""
        return self.script_status.copy()
    
    def is_running(self, script_name: str) -> bool:
        """Проверяет, выполняется ли скрипт"""
        return script_name in self.running_processes
    
    async def cancel_script(self, script_name: str) -> Dict:
        """Отменяет выполнение скрипта"""
        if script_name not in self.running_processes:
            return {
                "status": "error",
                "message": f"Скрипт {script_name} не выполняется"
            }
        
        try:
            process = self.running_processes[script_name]
            process.kill()
            await process.wait()
            
            self.script_status[script_name].update({
                "status": ScriptStatus.CANCELLED.value,
                "completed_at": datetime.utcnow().isoformat()
            })
            
            del self.running_processes[script_name]
            
            return {
                "status": "success",
                "message": f"Скрипт {script_name} отменен"
            }
        except Exception as e:
            logger.error(f"Ошибка при отмене скрипта {script_name}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_available_scripts(self) -> List[str]:
        """Возвращает список доступных ML-скриптов"""
        scripts = []
        for file in self.scripts_directory.glob("*.py"):
            if file.name not in ["__init__.py", "config.py"]:
                scripts.append(file.name)
        return sorted(scripts)

