"""
Configuración centralizada del sistema de agentes LDAP
"""
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class LDAPConfig:
    """Configuración del servidor LDAP"""
    server_url: str = os.getenv("LDAP_SERVER", "ldap://localhost:389")
    bind_dn: str = os.getenv("LDAP_ADMIN_DN", "cn=admin,dc=meli,dc=com")
    bind_password: str = os.getenv("LDAP_ADMIN_PASSWORD", "")
    base_dn: str = os.getenv("LDAP_BASE_DN", "dc=meli,dc=com")
    timeout: int = 10
    pool_size: int = 5

@dataclass
class AIConfig:
    """Configuración de la IA"""
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    model: str = "gemini-2.0-flash"
    temperature: float = 0.3
    max_tokens: int = 2048

@dataclass
class SystemConfig:
    """Configuración del sistema"""
    project_root: Path = Path(__file__).parent.parent
    tools_dir: Path = Path(__file__).parent / "generated_tools"
    persistence_file: Path = Path(__file__).parent / "tools_registry.yaml"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    max_retries: int = 3
    
    def __post_init__(self):
        self.tools_dir.mkdir(exist_ok=True)

# Instancias globales
ldap_config = LDAPConfig()
ai_config = AIConfig()
system_config = SystemConfig()
