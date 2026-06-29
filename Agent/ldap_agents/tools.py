"""
Herramientas base y ofensivas para consultas LDAP
Define las funcionalidades iniciales del sistema de agentes
"""
from typing import Dict, Any, List, Callable
from functools import wraps
from loguru import logger
import json

from .connector import get_ldap_connector

# ==================== HERRAMIENTAS BASE ====================

def get_current_user_info() -> Dict[str, Any]:
    """
    HERRAMIENTA BASE: Obtiene información del usuario actual ejecutando el agente

    Retorna:
        - username: Usuario del sistema
        - Información de LDAP (si existe)
        - Grupos del usuario
    """
    try:
        connector = get_ldap_connector()
        result = connector.get_current_user_info()
        return {
            "success": True,
            "username": result.get("username"),
            "attributes": result.get("info", {}),
            "groups": result.get("groups", [])
        }
    except Exception as e:
        logger.error(f"Error en get_current_user_info: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_user_groups(username: str) -> Dict[str, Any]:
    """
    HERRAMIENTA BASE: Obtiene grupos de un usuario específico
    
    Args:
        username: Nombre del usuario LDAP
    
    Retorna:
        - Lista de grupos del usuario
    """
    try:
        connector = get_ldap_connector()
        groups = connector.get_user_groups(username)
        return {
            "success": True,
            "username": username,
            "groups": groups,
            "group_count": len(groups)
        }
    except Exception as e:
        logger.error(f"Error en get_user_groups({username}): {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ==================== HERRAMIENTAS OFENSIVAS ====================

def get_all_users() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Recopila lista completa de usuarios del dominio
    
    🎯 Caso de uso: Reconocimiento inicial (Phase 1 - Recon)
    - Identificar objetivos potenciales
    - Detectar patrones de nombres
    - Encontrar cuentas especiales/de servicio
    """
    try:
        connector = get_ldap_connector()
        users = connector.get_all_users()
        
        # Análisis ofensivo básico
        user_list = []
        service_accounts = []
        
        for user in users:
            uid = user.get('uid', ['unknown'])[0]
            cn = user.get('cn', ['unknown'])[0]
            mail = user.get('mail', ['N/A'])[0]
            
            user_entry = {
                'uid': uid,
                'cn': cn,
                'mail': mail
            }
            user_list.append(user_entry)
            
            # Detectar cuentas de servicio (patrón común)
            if any(keyword in uid.lower() for keyword in ['svc', 'service', 'bot', 'admin', 'root']):
                service_accounts.append(uid)
        
        return {
            "success": True,
            "total_users": len(user_list),
            "users": user_list,
            "potential_service_accounts": service_accounts,
            "recon_level": "basic_enumeration"
        }
    except Exception as e:
        logger.error(f"Error en get_all_users: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_all_groups() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Enumeración completa de grupos del dominio
    
    🎯 Caso de uso: Mapeo de estructura (Phase 2 - Enumeration)
    - Identificar grupos privados
    - Detectar grupos administrativos
    - Mapear relaciones de permisos
    """
    try:
        connector = get_ldap_connector()
        groups = connector.get_all_groups()
        
        # Análisis ofensivo
        privileged_patterns = ['admin', 'domain admin', 'administrators', 'root', 'sudo', 'wheel', 'operators']
        sensitive_groups = []
        
        group_list = []
        for group in groups:
            cn = group.get('cn', ['unknown'])[0]
            member_count = len(group.get('member', []))
            
            group_entry = {
                'cn': cn,
                'member_count': member_count,
                'members': group.get('member', [])[:5]  # Primeros 5 miembros
            }
            group_list.append(group_entry)
            
            if any(pattern in cn.lower() for pattern in privileged_patterns):
                sensitive_groups.append(cn)
        
        return {
            "success": True,
            "total_groups": len(group_list),
            "groups": group_list,
            "sensitive_groups": sensitive_groups,
            "analysis": "Look for high-privilege groups for privilege escalation vectors"
        }
    except Exception as e:
        logger.error(f"Error en get_all_groups: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_user_memberships_recursive(username: str) -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Análisis de membresías recursivas (nested groups)
    
    🎯 Caso de uso: Evaluación de permisos (Phase 3 - Privilege Analysis)
    - Detectar membresías heredadas
    - Identificar tokens amplificados
    - Planear escalada de privilegios
    """
    try:
        connector = get_ldap_connector()
        result = connector.get_user_memberships_recursive(username)
        
        if "error" in result:
            return {"success": False, "error": result["error"]}
        
        # Análisis ofensivo
        all_groups = set(result['direct_groups']) | set(result['nested_groups'])
        privilege_escalation_keywords = ['admin', 'sudo', 'wheel', 'domain', 'root']
        
        risky_groups = [g for g in all_groups 
                       if any(keyword in g.lower() for keyword in privilege_escalation_keywords)]
        
        return {
            "success": True,
            "username": username,
            "direct_groups": result['direct_groups'],
            "nested_groups": result['nested_groups'],
            "total_effective_groups": len(all_groups),
            "risky_groups": risky_groups,
            "privilege_escalation_potential": len(risky_groups) > 0
        }
    except Exception as e:
        logger.error(f"Error en get_user_memberships_recursive({username}): {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_user_full_info(username: str) -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Obtiene TODOS los atributos de un usuario específico
    
    🎯 Caso de uso: Investigación dirigida (Phase 4 - Targeted Recon)
    - Inspección completa de un objetivo puntual (no solo los campos básicos)
    - Detectar atributos no estándar con datos ocultos (pager, info, etc.)
    
    Args:
        username: Nombre del usuario LDAP (uid). Ej: user-info john.doe
    """
    try:
        connector = get_ldap_connector()
        user_info = connector.get_user_info(username)
        
        if not user_info:
            return {
                "success": False,
                "error": f"Usuario '{username}' no encontrado"
            }
        
        return {
            "success": True,
            "username": username,
            "attributes": user_info
        }
    except Exception as e:
        logger.error(f"Error en get_user_full_info({username}): {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_all_computers() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Enumera todas las computadoras del dominio
    
    🎯 Caso de uso: Reconocimiento de activos (Phase 1 - Recon)
    - Identificar equipos unidos al dominio
    - Detectar servidores vs estaciones de trabajo
    """
    try:
        connector = get_ldap_connector()
        computers = connector.get_all_computers()
        
        return {
            "success": True,
            "total_computers": len(computers),
            "computers": computers
        }
    except Exception as e:
        logger.error(f"Error en get_all_computers: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_all_shares() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Enumera todos los shares del dominio
    
    🎯 Caso de uso: Reconocimiento de recursos compartidos (Phase 1 - Recon)
    - Identificar shares accesibles dentro del dominio
    - Detectar shares con nombres sensibles (backup, finance, etc.)
    """
    try:
        connector = get_ldap_connector()
        shares = connector.get_all_shares()
        
        return {
            "success": True,
            "total_shares": len(shares),
            "shares": shares
        }
    except Exception as e:
        logger.error(f"Error en get_all_shares: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_domain_info() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Información del dominio LDAP
    
    🎯 Caso de uso: Recon pasivo (Phase 0 - Initial Recon)
    - Identificar estructura del dominio
    - Detectar configuración
    - Planificar estrategia de ataque
    """
    try:
        connector = get_ldap_connector()
        result = connector.get_domain_info()
        
        return {
            "success": True,
            "domain_info": result,
            "security_notes": [
                "Check for forest trusts",
                "Identify domain functional level",
                "Look for misconfigured ACLs"
            ]
        }
    except Exception as e:
        logger.error(f"Error en get_domain_info: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def get_adcs_templates() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Enumera templates de ADCS para análisis de misconfiguraciones

    🎯 Caso de uso: Privilege Escalation vía ADCS (Phase 5)
    Busca condiciones de las vulnerabilidades ESC1-ESC13:
    - ESC1: Template permite al solicitante especificar el SAN
    - ESC2: Template permite propósito cualquiera (Any Purpose EKU)
    - ESC3: Template con EKU de Certificate Request Agent
    """
    try:
        connector = get_ldap_connector()
        templates = connector.get_adcs_templates()

        # Análisis automático de condiciones ESC
        vulnerable = []
        for t in templates:
            cn = t.get('cn', ['?'])[0] if isinstance(t.get('cn'), list) else t.get('cn', '?')
            flags = {}

            name_flag = t.get('msPKI-Certificate-Name-Flag', [None])
            if isinstance(name_flag, list):
                name_flag = name_flag[0]
            if name_flag:
                try:
                    val = int(name_flag)
                    flags['ESC1_candidate'] = bool(val & 0x1)  # ENROLLEE_SUPPLIES_SUBJECT
                except (ValueError, TypeError):
                    pass

            eku = t.get('pkiExtendedKeyUsage', [])
            any_purpose = '2.5.29.37.0' in eku
            client_auth = '1.3.6.1.5.5.7.3.2' in eku
            flags['ESC2_candidate'] = any_purpose
            flags['has_client_auth'] = client_auth

            ra_sig = t.get('msPKI-RA-Signature', [None])
            if isinstance(ra_sig, list):
                ra_sig = ra_sig[0]
            if ra_sig:
                try:
                    flags['ESC3_candidate'] = int(ra_sig) == 0
                except (ValueError, TypeError):
                    pass

            if any(flags.values()):
                vulnerable.append({'cn': cn, 'flags': flags})

        return {
            "success": True,
            "total_templates": len(templates),
            "templates": templates,
            "potentially_vulnerable": vulnerable,
            "note": "Sin templates ADCS si el servidor es OpenLDAP puro (no Windows AD)"
        }
    except Exception as e:
        logger.error(f"Error en get_adcs_templates: {e}")
        return {"success": False, "error": str(e)}


def get_gpos() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Enumera todas las Group Policy Objects del dominio

    🎯 Caso de uso: Lateral Movement / Persistence (Phase 4)
    - Identificar GPOs que aplican scripts de inicio/logon
    - Detectar GPOs con configuraciones de seguridad débiles
    - Encontrar GPOs que despliegan software (posible DLL hijacking)
    """
    try:
        connector = get_ldap_connector()
        gpos = connector.get_gpos()

        gpo_list = []
        for gpo in gpos:
            cn = gpo.get('cn', ['?'])[0] if isinstance(gpo.get('cn'), list) else gpo.get('cn', '?')
            name = gpo.get('displayName', ['Sin nombre'])
            if isinstance(name, list):
                name = name[0]
            path = gpo.get('gPCFileSysPath', ['N/A'])
            if isinstance(path, list):
                path = path[0]

            gpo_list.append({'cn': cn, 'name': name, 'sysvol_path': path})

        return {
            "success": True,
            "total_gpos": len(gpo_list),
            "gpos": gpo_list,
            "note": "Sin GPOs si el servidor es OpenLDAP puro (no Windows AD)"
        }
    except Exception as e:
        logger.error(f"Error en get_gpos: {e}")
        return {"success": False, "error": str(e)}


def get_policies() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Obtiene políticas de contraseñas del dominio

    🎯 Caso de uso: Password Spraying / Brute Force planning (Phase 2)
    - Identificar longitud mínima de contraseña
    - Detectar umbral de lockout (para no triggear bloqueos)
    - Encontrar Fine-Grained Policies que aplican a cuentas específicas
    """
    try:
        connector = get_ldap_connector()
        result = connector.get_policies()

        domain_pol = result.get('domain_policy', {})

        def decode_val(v):
            if isinstance(v, list):
                v = v[0] if v else None
            if isinstance(v, bytes):
                v = v.decode('utf-8')
            return v

        parsed = {
            'pwd_history_length': decode_val(domain_pol.get('pwdHistoryLength')),
            'pwd_min_length': decode_val(domain_pol.get('pwdMinLength')),
            'pwd_max_age_days': None,
            'pwd_min_age_days': None,
            'lockout_threshold': decode_val(domain_pol.get('lockoutThreshold')),
            'lockout_duration_mins': None,
        }

        # Convertir intervalos de 100-nanosegundos a días/minutos
        max_age = decode_val(domain_pol.get('pwdMaxAge'))
        if max_age and max_age != '0':
            try:
                parsed['pwd_max_age_days'] = abs(int(max_age)) // (10_000_000 * 86400)
            except (ValueError, TypeError):
                pass

        lockout_dur = decode_val(domain_pol.get('lockoutDuration'))
        if lockout_dur and lockout_dur != '0':
            try:
                parsed['lockout_duration_mins'] = abs(int(lockout_dur)) // (10_000_000 * 60)
            except (ValueError, TypeError):
                pass

        return {
            "success": True,
            "domain_password_policy": parsed,
            "fine_grained_policies": result.get('fine_grained_policies', []),
            "spray_safe_threshold": parsed.get('lockout_threshold'),
        }
    except Exception as e:
        logger.error(f"Error en get_policies: {e}")
        return {"success": False, "error": str(e)}


def get_spns() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Enumera Service Principal Names para Kerberoasting

    🎯 Caso de uso: Credential Access (Phase 3 - Kerberoasting)
    - Identificar cuentas de servicio con SPNs (targets de Kerberoasting)
    - Cuentas de servicio frecuentemente tienen contraseñas débiles/viejas
    - GetUserSPNs.py (Impacket) usa la misma lógica
    """
    try:
        connector = get_ldap_connector()
        accounts = connector.get_spns()

        spn_list = []
        for account in accounts:
            uid = account.get('uid', account.get('cn', ['?']))
            if isinstance(uid, list):
                uid = uid[0]
            spns = account.get('servicePrincipalName', [])
            if isinstance(spns, str):
                spns = [spns]

            spn_list.append({'account': uid, 'spns': spns, 'spn_count': len(spns)})

        return {
            "success": True,
            "total_kerberoastable": len(spn_list),
            "accounts": spn_list,
            "attack_note": "Usar GetUserSPNs.py o Rubeus para solicitar TGS y crackear offline"
        }
    except Exception as e:
        logger.error(f"Error en get_spns: {e}")
        return {"success": False, "error": str(e)}


def get_delegations() -> Dict[str, Any]:
    """
    HERRAMIENTA OFENSIVA: Enumera cuentas/equipos con delegación Kerberos configurada

    🎯 Caso de uso: Privilege Escalation / Lateral Movement (Phase 4)
    - Unconstrained Delegation: compromiso total del equipo → TGTs de cualquier usuario
    - Constrained Delegation: puede impersonar usuarios hacia servicios específicos
    - RBCD: Resource-Based Constrained Delegation (posible con permisos de escritura)
    """
    try:
        connector = get_ldap_connector()
        result = connector.get_delegations()

        def extract_names(entries):
            names = []
            for e in entries:
                cn = e.get('cn', e.get('uid', ['?']))
                if isinstance(cn, list):
                    cn = cn[0]
                allowed = e.get('msDS-AllowedToDelegateTo', [])
                names.append({'account': cn, 'delegates_to': allowed})
            return names

        unconstrained = extract_names(result.get('unconstrained', []))
        constrained = extract_names(result.get('constrained', []))
        rbcd = extract_names(result.get('resource_based', []))

        return {
            "success": True,
            "unconstrained_delegation": unconstrained,
            "constrained_delegation": constrained,
            "resource_based_delegation": rbcd,
            "high_risk": len(unconstrained) > 0,
            "attack_note": "Unconstrained delegation → usar Rubeus monitor /interval para capturar TGTs"
        }
    except Exception as e:
        logger.error(f"Error en get_delegations: {e}")
        return {"success": False, "error": str(e)}


# ==================== REGISTRO DE HERRAMIENTAS ====================

BASE_TOOLS = {
    'get_current_user_info': {
        'function': get_current_user_info,
        'description': 'Obtiene información del usuario actual ejecutando el agente',
        'category': 'base',
        'params': {}
    },
    'get_user_groups': {
        'function': get_user_groups,
        'description': 'Obtiene grupos de un usuario específico',
        'category': 'base',
        'params': {'username': 'str'}
    }
}

OFFENSIVE_TOOLS = {
    'get_all_users': {
        'function': get_all_users,
        'description': 'Enumera todos los usuarios del dominio (LDAP Enumeration)',
        'category': 'offensive',
        'phase': 'Recon',
        'params': {}
    },
    'get_all_groups': {
        'function': get_all_groups,
        'description': 'Enumera todos los grupos del dominio',
        'category': 'offensive',
        'phase': 'Enumeration',
        'params': {}
    },
    'get_user_memberships_recursive': {
        'function': get_user_memberships_recursive,
        'description': 'Analiza membresías anidadas para evaluación de privilegios',
        'category': 'offensive',
        'phase': 'Privilege Analysis',
        'params': {'username': 'str'}
    },
    'get_user_full_info': {
        'function': get_user_full_info,
        'description': 'Obtiene TODOS los atributos de un usuario específico (inspección completa)',
        'category': 'offensive',
        'phase': 'Targeted Recon',
        'params': {'username': 'str'}
    },
    'get_all_computers': {
        'function': get_all_computers,
        'description': 'Enumera todas las computadoras del dominio',
        'category': 'offensive',
        'phase': 'Recon',
        'params': {}
    },
    'get_all_shares': {
        'function': get_all_shares,
        'description': 'Enumera todos los shares del dominio',
        'category': 'offensive',
        'phase': 'Recon',
        'params': {}
    },
    'get_domain_info': {
        'function': get_domain_info,
        'description': 'Obtiene información del dominio LDAP',
        'category': 'offensive',
        'phase': 'Initial Recon',
        'params': {}
    },
    'get_adcs_templates': {
        'function': get_adcs_templates,
        'description': 'Enumera templates ADCS para detección de ESC1-ESC13',
        'category': 'offensive',
        'phase': 'Privilege Escalation',
        'params': {}
    },
    'get_gpos': {
        'function': get_gpos,
        'description': 'Enumera todas las Group Policy Objects del dominio',
        'category': 'offensive',
        'phase': 'Lateral Movement',
        'params': {}
    },
    'get_policies': {
        'function': get_policies,
        'description': 'Obtiene políticas de contraseñas del dominio (domain + PSOs)',
        'category': 'offensive',
        'phase': 'Credential Access',
        'params': {}
    },
    'get_spns': {
        'function': get_spns,
        'description': 'Enumera SPNs para Kerberoasting (cuentas de servicio con ticket TGS)',
        'category': 'offensive',
        'phase': 'Credential Access',
        'params': {}
    },
    'get_delegations': {
        'function': get_delegations,
        'description': 'Enumera delegación Kerberos (Unconstrained, Constrained, RBCD)',
        'category': 'offensive',
        'phase': 'Privilege Escalation',
        'params': {}
    }
}

# Todas las herramientas disponibles
ALL_TOOLS = {**BASE_TOOLS, **OFFENSIVE_TOOLS}


def get_tools_registry() -> Dict[str, Dict[str, Any]]:
    """Retorna el registro completo de herramientas"""
    return ALL_TOOLS


def tool_exists(tool_name: str) -> bool:
    """Verifica si una herramienta existe"""
    return tool_name in ALL_TOOLS


def call_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Ejecuta una herramienta por nombre"""
    if tool_name not in ALL_TOOLS:
        return {
            "success": False,
            "error": f"Herramienta no encontrada: {tool_name}"
        }
    
    try:
        func = ALL_TOOLS[tool_name]['function']
        result = func(**kwargs)
        return result
    except Exception as e:
        logger.error(f"Error ejecutando {tool_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }
