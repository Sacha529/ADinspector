"""
Conector LDAP para interactuar con servidores OpenLDAP
Proporciona abstracciones para queries comunes en contextos de seguridad ofensiva
"""
import ldap
from ldap import modlist as mod
from typing import List, Dict, Any, Optional
from loguru import logger
from ldap.filter import escape_filter_chars
import json

from .config import ldap_config

class LDAPConnector:
    """Conector seguro y eficiente para OpenLDAP"""
    
    def __init__(self):
        self.server_url = ldap_config.server_url
        self.bind_dn = ldap_config.bind_dn
        self.bind_password = ldap_config.bind_password
        self.base_dn = ldap_config.base_dn
        self.timeout = ldap_config.timeout
        self.conn: Optional[ldap.ldapobject.LDAPObject] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establece conexión con el servidor LDAP"""
        try:
            ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, self.timeout)
            self.conn = ldap.initialize(self.server_url)
            self.conn.set_option(ldap.OPT_REFERRALS, 0)
            self.conn.simple_bind_s(self.bind_dn, self.bind_password)
            logger.info(f"✅ Conectado a LDAP: {self.server_url}")
        except ldap.INVALID_CREDENTIALS:
            logger.error("❌ Credenciales LDAP inválidas")
            raise
        except ldap.SERVER_DOWN:
            logger.error(f"❌ Servidor LDAP no disponible: {self.server_url}")
            raise
        except Exception as e:
            logger.error(f"❌ Error conectando a LDAP: {e}")
            raise

    def _reconnect(self) -> None:
        """Reconecta al servidor LDAP si la conexión se perdió"""
        logger.info("🔄 Reconectando a LDAP...")
        self.conn = None
        self._connect()
    
    def search(self, search_filter: str, attributes: List[str] = None, 
               search_base: str = None) -> List[Dict[str, Any]]:
        """
        Realiza búsqueda LDAP genérica
        
        Args:
            search_filter: Filtro LDAP (ej: "(uid=*)")
            attributes: Atributos a retornar
            search_base: Base DN para búsqueda (default: self.base_dn)
        
        Returns:
            Lista de resultados como diccionarios
        """
        if not self.conn:
            self._connect()
        
        search_base = search_base or self.base_dn
        attributes = attributes or []
        
        try:
            results = self.conn.search_s(
                search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                attributes
            )
        except ldap.SERVER_DOWN:
            logger.warning("⚠️ Conexión LDAP caída, reconectando...")
            self._reconnect()
            results = self.conn.search_s(
                search_base,
                ldap.SCOPE_SUBTREE,
                search_filter,
                attributes
            )
        except ldap.FILTER_ERROR as e:
            logger.error(f"❌ Filtro LDAP inválido: {e}")
            raise ValueError(f"Filtro LDAP inválido: {search_filter}")
        except Exception as e:
            logger.error(f"❌ Error en búsqueda LDAP: {e}")
            raise

        try:
            formatted = []
            for dn, attrs in results:
                if dn is None:
                    continue

                entry = {"dn": dn}
                for key, values in attrs.items():
                    if isinstance(values, list):
                        entry[key] = [v.decode('utf-8') if isinstance(v, bytes) else v
                                     for v in values]
                    else:
                        entry[key] = values
                formatted.append(entry)

            logger.debug(f"🔍 Búsqueda LDAP retornó {len(formatted)} resultados")
            return formatted
        except Exception as e:
            logger.error(f"❌ Error procesando resultados LDAP: {e}")
            raise
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Obtiene información detallada de un usuario"""
        filter_str = f"(uid={escape_filter_chars(username)})"
        results = self.search(filter_str)
        return results[0] if results else None
    
    def get_user_groups(self, username: str) -> List[str]:
        """Obtiene grupos de un usuario específico"""
        user_info = self.get_user_info(username)
        if not user_info:
            return []
        
        user_dn = user_info.get("dn")
        
        # Búsqueda de grupos que contienen este usuario
        filter_str = f"(|(member={escape_filter_chars(user_dn)})(memberUid={escape_filter_chars(username)}))"
        results = self.search(filter_str, ["cn"])
        
        return [r.get("cn", ["unknown"])[0] for r in results]
    
    def get_current_user_info(self) -> Dict[str, Any]:
        """Obtiene información del usuario LDAP actual (extraído del bind DN)"""
        # Derivar el username del bind DN: "cn=admin,dc=meli,dc=com" → "admin"
        try:
            current_user = self.bind_dn.split(',')[0].split('=')[1]
        except (IndexError, AttributeError):
            current_user = self.bind_dn

        info = self.get_user_info(current_user)
        if not info:
            return {
                "username": current_user,
                "bind_dn": self.bind_dn,
                "status": "not_found_in_ldap",
                "message": f"Usuario '{current_user}' autenticado pero sin entrada uid en el directorio"
            }

        groups = self.get_user_groups(current_user)
        return {
            "username": current_user,
            "bind_dn": self.bind_dn,
            "info": info,
            "groups": groups
        }
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Obtiene lista de todos los usuarios del dominio (Ofensiva)"""
        filter_str = "(uid=*)"
        results = self.search(filter_str, ["uid", "cn", "mail", "description"])
        return results
    
    def get_all_groups(self) -> List[Dict[str, Any]]:
        """Obtiene lista de todos los grupos del dominio (Ofensiva)"""
        # Nota: se removió "(cn=*)" del filtro porque los usuarios también
        # tienen atributo cn, lo que hacía que esta búsqueda devolviera
        # usuarios y grupos mezclados.
        filter_str = "(|(objectClass=groupOfNames)(objectClass=groupOfUniqueNames))"
        results = self.search(filter_str, ["cn", "member", "memberUid", "description"])
        return results
    
    def get_all_computers(self) -> List[Dict[str, Any]]:
        """
        Obtiene lista de todas las computadoras del dominio (Ofensiva)
        
        Busca dentro de ou=computers,<base_dn>. Si la OU no existe todavía
        en el directorio, devuelve lista vacía en lugar de fallar.
        """
        search_base = f"ou=computers,{self.base_dn}"
        filter_str = "(!(objectClass=organizationalUnit))"
        try:
            return self.search(filter_str, [], search_base=search_base)
        except ldap.NO_SUCH_OBJECT:
            logger.warning(f"⚠️ No existe la OU 'ou=computers' en {self.base_dn}")
            return []
    
    def get_all_shares(self) -> List[Dict[str, Any]]:
        """
        Obtiene lista de todos los shares del dominio (Ofensiva)
        
        Busca dentro de ou=shares,<base_dn>. Si la OU no existe todavía
        en el directorio, devuelve lista vacía en lugar de fallar.
        """
        search_base = f"ou=shares,{self.base_dn}"
        filter_str = "(!(objectClass=organizationalUnit))"
        try:
            return self.search(filter_str, [], search_base=search_base)
        except ldap.NO_SUCH_OBJECT:
            logger.warning(f"⚠️ No existe la OU 'ou=shares' en {self.base_dn}")
            return []
    
    def get_domain_info(self) -> Dict[str, Any]:
        """Obtiene información del dominio LDAP (Ofensiva)"""
        try:
            results = self.search("(objectClass=dcObject)", ["dc", "o", "description"], 
                                 search_base=self.base_dn)
            return {
                "base_dn": self.base_dn,
                "domain_info": results,
                "server": self.server_url
            }
        except Exception as e:
            logger.error(f"❌ Error obteniendo info del dominio: {e}")
            return {"error": str(e)}
    
    def get_user_memberships_recursive(self, username: str) -> Dict[str, Any]:
        """
        Obtiene membresías recursivas de un usuario (Ofensiva)
        Útil para identificar permisos heredados
        """
        user_info = self.get_user_info(username)
        if not user_info:
            return {"error": f"Usuario {username} no encontrado"}
        
        user_dn = user_info.get("dn")
        direct_groups = self.get_user_groups(username)
        
        # Búsqueda recursiva: grupos que contienen los grupos del usuario
        nested_groups = set(direct_groups)
        for group in direct_groups:
            filter_str = f"(cn={escape_filter_chars(group)})"
            results = self.search(filter_str, ["memberOf"])
            for result in results:
                member_of = result.get("memberOf", [])
                for parent_group_dn in member_of:
                    if "cn=" in parent_group_dn:
                        group_name = parent_group_dn.split(",")[0].replace("cn=", "")
                        nested_groups.add(group_name)
        
        return {
            "username": username,
            "direct_groups": direct_groups,
            "nested_groups": list(nested_groups)
        }
    
    def get_adcs_templates(self) -> List[Dict[str, Any]]:
        """
        Enumera templates de ADCS para análisis de misconfiguraciones (ESC1-ESC13)

        Busca en CN=Certificate Templates dentro del naming context de configuración.
        Devuelve lista vacía si el entorno no tiene ADCS (ej. OpenLDAP puro).
        """
        config_dn = f"CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,{self.base_dn}"
        filter_str = "(objectClass=pKICertificateTemplate)"
        attrs = [
            'cn', 'displayName',
            'msPKI-Certificate-Name-Flag',   # ESC1: ENROLLEE_SUPPLIES_SUBJECT
            'msPKI-Enrollment-Flag',         # ESC1: PEND_ALL_REQUESTS
            'msPKI-RA-Signature',            # ESC3: Certificate Request Agent
            'pkiExtendedKeyUsage',           # EKU: client auth, any purpose
            'msPKI-Certificate-Application-Policy',
        ]
        try:
            return self.search(filter_str, attrs, search_base=config_dn)
        except ldap.NO_SUCH_OBJECT:
            logger.warning("⚠️ ADCS: CN=Certificate Templates no encontrado en este directorio")
            return []
        except Exception as e:
            logger.error(f"❌ Error enumerando ADCS templates: {e}")
            return []

    def get_gpos(self) -> List[Dict[str, Any]]:
        """Enumera todas las GPOs del dominio"""
        search_base = f"CN=Policies,CN=System,{self.base_dn}"
        filter_str = "(objectClass=groupPolicyContainer)"
        attrs = ['cn', 'displayName', 'gPCFileSysPath', 'versionNumber', 'flags', 'description']
        try:
            return self.search(filter_str, attrs, search_base=search_base)
        except ldap.NO_SUCH_OBJECT:
            logger.warning("⚠️ GPOs: CN=Policies,CN=System no encontrado en este directorio")
            return []
        except Exception as e:
            logger.error(f"❌ Error enumerando GPOs: {e}")
            return []

    def get_policies(self) -> Dict[str, Any]:
        """Obtiene las políticas de dominio y de contraseñas (domain + fine-grained PSOs)"""
        password_attrs = [
            'pwdHistoryLength', 'pwdMaxAge', 'pwdMinAge',
            'pwdMinLength', 'pwdProperties',
            'lockoutDuration', 'lockoutObservationWindow', 'lockoutThreshold',
        ]
        domain_policy = self.search("(objectClass=domain)", password_attrs, search_base=self.base_dn)

        pso_base = f"CN=Password Settings Container,CN=System,{self.base_dn}"
        try:
            pso_policies = self.search("(objectClass=msDS-PasswordSettings)", [], search_base=pso_base)
        except ldap.NO_SUCH_OBJECT:
            logger.warning("⚠️ PSO: CN=Password Settings Container no encontrado")
            pso_policies = []
        except Exception:
            pso_policies = []

        return {
            "domain_policy": domain_policy[0] if domain_policy else {},
            "fine_grained_policies": pso_policies,
        }

    def get_spns(self) -> List[Dict[str, Any]]:
        """
        Enumera todas las cuentas con Service Principal Names (SPNs)
        para análisis de Kerberoasting.
        """
        filter_str = "(servicePrincipalName=*)"
        attrs = ['uid', 'cn', 'mail', 'servicePrincipalName', 'description', 'userAccountControl']
        return self.search(filter_str, attrs)

    def get_delegations(self) -> Dict[str, Any]:
        """
        Enumera cuentas y equipos con delegación configurada.

        Tipos buscados:
        - Unconstrained: userAccountControl bit 0x80000 (524288) o 0x1000000 (computers)
        - Constrained: msDS-AllowedToDelegateTo poblado
        - RBCD: msDS-AllowedToActOnBehalfOfOtherIdentity presente
        """
        attrs = ['cn', 'uid', 'servicePrincipalName', 'msDS-AllowedToDelegateTo',
                 'userAccountControl', 'description']

        def safe_search(f):
            try:
                return self.search(f, attrs)
            except Exception as e:
                logger.warning(f"⚠️ Delegación: búsqueda fallida ({e})")
                return []

        unconstrained = safe_search(
            "(|(userAccountControl:1.2.840.113556.1.4.803:=524288)"
            "(userAccountControl:1.2.840.113556.1.4.803:=16777216))"
        )
        constrained = safe_search("(msDS-AllowedToDelegateTo=*)")
        rbcd = safe_search("(msDS-AllowedToActOnBehalfOfOtherIdentity=*)")

        return {
            "unconstrained": unconstrained,
            "constrained": constrained,
            "resource_based": rbcd,
        }

    def close(self) -> None:
        """Cierra la conexión LDAP"""
        if self.conn:
            try:
                self.conn.unbind_s()
                logger.info("✅ Conexión LDAP cerrada")
            except Exception as e:
                logger.error(f"Error cerrando conexión LDAP: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Singleton para acceso global
_connector: Optional[LDAPConnector] = None

def get_ldap_connector() -> LDAPConnector:
    """Obtiene instancia singleton del conector LDAP"""
    global _connector
    if _connector is None:
        _connector = LDAPConnector()
    return _connector
