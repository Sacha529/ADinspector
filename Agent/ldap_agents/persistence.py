"""
Sistema de persistencia YAML para herramientas auto-generadas
Permite guardar, cargar y validar herramientas entre sesiones
"""
import yaml
import hashlib
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from loguru import logger

from .config import system_config

class ToolRegistry:
    """Registro persistente de herramientas auto-generadas"""
    
    def __init__(self, registry_file: Path = None):
        self.registry_file = registry_file or system_config.persistence_file
        self.registry: Dict[str, Dict[str, Any]] = {}
        self.load()
    
    def load(self) -> None:
        """Carga el registro de herramientas desde archivo YAML"""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    self.registry = data.get('tools', {})
                logger.info(f"✅ Registro de herramientas cargado: {len(self.registry)} herramientas")
            except Exception as e:
                logger.error(f"❌ Error cargando registro: {e}")
                self.registry = {}
        else:
            logger.info("📝 Creando nuevo registro de herramientas")
            self.registry = {}
    
    def save(self) -> None:
        """Guarda el registro en archivo YAML"""
        try:
            data = {
                'metadata': {
                    'version': '1.0',
                    'last_updated': datetime.now().isoformat(),
                    'total_tools': len(self.registry)
                },
                'tools': self.registry
            }
            
            with open(self.registry_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"💾 Registro guardado: {len(self.registry)} herramientas")
        except Exception as e:
            logger.error(f"❌ Error guardando registro: {e}")
    
    def register_tool(self, name: str, code: str, metadata: Dict[str, Any] = None) -> None:
        """
        Registra una herramienta auto-generada
        
        Args:
            name: Nombre único de la herramienta
            code: Código Python de la herramienta
            metadata: Información adicional (descripción, generado_por, etc.)
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        self.registry[name] = {
            'code': code,
            'code_hash': code_hash,
            'created_at': datetime.now().isoformat(),
            'metadata': metadata or {},
            'status': 'active'
        }
        self.save()
        logger.info(f"✅ Herramienta registrada: {name}")
    
    def get_tool(self, name: str) -> Dict[str, Any]:
        """Obtiene código y metadata de una herramienta"""
        return self.registry.get(name)
    
    def list_tools(self) -> List[str]:
        """Lista todas las herramientas disponibles"""
        return list(self.registry.keys())
    
    def remove_tool(self, name: str) -> bool:
        """Elimina una herramienta del registro"""
        if name in self.registry:
            del self.registry[name]
            self.save()
            logger.info(f"🗑️  Herramienta eliminada: {name}")
            return True
        return False
    
    def reset_to_defaults(self) -> None:
        """Restaura el registro a su estado original (sin herramientas generadas)"""
        self.registry = {}
        self.save()
        logger.info("♻️  Registro restaurado a estado original")
    
    def get_registry_info(self) -> Dict[str, Any]:
        """Obtiene información del registro"""
        return {
            'total_tools': len(self.registry),
            'tools': list(self.registry.keys()),
            'file': str(self.registry_file)
        }


# Instancia global del registro
_registry: ToolRegistry = None

def get_tool_registry() -> ToolRegistry:
    """Obtiene instancia singleton del registro de herramientas"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
