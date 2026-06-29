"""
Sistema de Agentes LDAP Auto-Adaptativos
Self-Expanding LDAP Agent System with Offensive Security Focus
"""

__version__ = "0.1.0"
__author__ = "Mercado Libre Offensive Security"

from .config import ldap_config, ai_config, system_config
from .connector import LDAPConnector, get_ldap_connector
from .tools import (
    get_current_user_info,
    get_user_groups,
    get_all_users,
    get_all_groups,
    get_user_memberships_recursive,
    get_user_full_info,
    get_all_computers,
    get_all_shares,
    get_domain_info,
    get_adcs_templates,
    get_gpos,
    get_policies,
    get_spns,
    get_delegations,
    get_tools_registry,
    call_tool,
    tool_exists
)
from .persistence import ToolRegistry, get_tool_registry
from .agents import (
    ExecutorAgent,
    GeneratorAgent,
    Coordinator
)

__all__ = [
    # Config
    'ldap_config',
    'ai_config',
    'system_config',
    # Connector
    'LDAPConnector',
    'get_ldap_connector',
    # Tools
    'get_current_user_info',
    'get_user_groups',
    'get_all_users',
    'get_all_groups',
    'get_user_memberships_recursive',
    'get_user_full_info',
    'get_all_computers',
    'get_all_shares',
    'get_domain_info',
    'get_tools_registry',
    'call_tool',
    'tool_exists',
    # Persistence
    'ToolRegistry',
    'get_tool_registry',
    # Agents
    'ExecutorAgent',
    'GeneratorAgent',
    'Coordinator'
]
