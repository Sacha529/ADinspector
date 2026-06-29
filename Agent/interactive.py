#!/usr/bin/env python3
"""
ADInspector - CLI Interactivo
Sistema de Agentes LDAP Auto-Adaptativos para Mercado Libre
"""

import json
from ldap_agents import Coordinator
from ldap_agents.tools import get_tools_registry
import readline
import os


class ADInspectorCLI:
    """CLI principal para ADInspector"""
    
    def __init__(self):
        print("⏳ Inicializando ADInspector...")
        print("🔫 Cargando municiones...")
        self.coordinator = Coordinator()
        print("🔍 Desplegando scanners de reconocimiento AD...")
        self.tools_info = get_tools_registry()
        print("🕵️  Activando al agente Smith...")
        self.running = True
        print("✅ Listo!\n")
    
    def print_banner(self):
        """Banner de bienvenida"""
        print(r"""
   ___    ____  ____                           __
  /   |  / __ \/  _/___  _________  ___  _____/ /_____  _____
 / /| | / / / // // __ \/ ___/ __ \/ _ \/ ___/ __/ __ \/ ___/
/ ___ |/ /_/ // // / / (__  ) /_/ /  __/ /__/ /_/ /_/ / /
/_/  |_/_____/___/_/ /_/____/ .___/\___/\___/\__/\____/_/
                            /_/
          Agentic  Active Directory Security Analyzer

          Mercado Libre - Offensive Security Team
""")
        print("✨ Características:")
        print("  • Consultas inteligentes a OpenLDAP")
        print("  • Auto-generación de herramientas con IA")
        print("  • Persistencia entre sesiones")
        print("  • Enfoque ofensivo (Red Team/Pentesting)")
        print("\n📖 Escribe 'help' para ver comandos disponibles\n")
    
    def print_help(self):
        """Muestra ayuda de comandos"""
        help_text = """
╔════════════════════════════════════════════════════════════════════════════╗
║                         COMANDOS DISPONIBLES                               ║
╚════════════════════════════════════════════════════════════════════════════╝

🤖 COMANDO INTELIGENTE:
  ask "<pregunta>"               - Pregunta a la IA (intenta herramientas primero)

📋 RECONOCIMIENTO:
  whoami                         - ¿Quién soy? (usuario sistema + LDAP)
  users                          - Enumerar todos los usuarios del dominio
  user-info <usuario>            - Todos los atributos LDAP de un usuario
  groups                         - Enumerar todos los grupos del dominio
  privilege [usuario]            - Analizar privilegios y grupos heredados
  computers                      - Listar computadoras del dominio
  shares                         - Listar shares del dominio
  domain                         - Información del dominio
  domain-enum-all                - Enumeración completa (todos los módulos)

🔴 OFENSIVOS AVANZADOS:
  adcs-templates                 - Enumerar templates ADCS (ESC1-ESC13)
  gpos                           - Enumerar Group Policy Objects
  policies                       - Políticas de contraseñas del dominio
  spns                           - Enumerar SPNs para Kerberoasting
  delegation                     - Delegación Kerberos (Unconstrained/Constrained/RBCD)

🛠️ SISTEMA:
  tools                          - Listar herramientas disponibles
  tools-generated                - Mostrar herramientas generadas por IA
  status                         - Estado del sistema
  reset                          - Restaurar a estado original
  persist                        - Ver info de persistencia

📚 OTRO:
  help                           - Este mensaje
  clear                          - Limpiar pantalla
  exit                           - Salir
        
"""
        print(help_text)
    
    def print_tools_summary(self):
        """Muestra resumen de herramientas"""
        print("\n" + "="*80)
        print("  📋 HERRAMIENTAS DISPONIBLES")
        print("="*80 + "\n")
        
        tools = self.tools_info
        print(f"🔧 HERRAMIENTAS ({len(tools)}):")
        
        # Mapear nombres de función a comandos reales
        command_map = {
            'get_current_user_info': 'whoami',
            'get_user_groups': 'groups [usuario]',
            'get_all_users': 'users',
            'get_all_groups': 'groups-all',
            'get_user_memberships_recursive': 'privilege [usuario]',
            'get_user_full_info': 'user-info <usuario>',
            'get_all_computers': 'computers',
            'get_all_shares': 'shares',
            'get_domain_info': 'domain'
        }
        
        for name in sorted(tools.keys()):
            info = tools[name]
            command = command_map.get(name, name)
            print(f"   • {command}")
            print(f"     └─ {info['description']}\n")
        
        generated_tools = self.coordinator.get_status()['generated_tools']
        if generated_tools:
            print(f"✨ HERRAMIENTAS GENERADAS ({len(generated_tools)}):")
            for tool in generated_tools:
                print(f"   • {tool}\n")
    
    def execute_command(self, cmd: str):
        """Ejecuta un comando del usuario"""
        parts = cmd.strip().split(maxsplit=1)
        if not parts:
            return
        
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Comandos de sistema
        if command == 'help':
            self.print_help()
        elif command == 'clear':
            os.system('clear' if os.name != 'nt' else 'cls')
        elif command == 'exit' or command == 'quit':
            self.running = False
            print("\n🚀 See you, Space Cowboy...\n")
        elif command == 'tools':
            self.print_tools_summary()
        elif command == 'tools-generated':
            self._show_generated_tools()
        elif command == 'status':
            self._show_status()
        elif command == 'reset':
            self._confirm_reset()
        elif command == 'persist':
            self._show_persistence_info()
        
        # Comandos de consulta
        elif command == 'ask':
            if not args:
                print("❌ Uso: ask \"<pregunta>\"")
                return
            query = args.strip('"\'')
            self._ask_ai(query)
        elif command == 'whoami':
            self._execute_tool('get_current_user_info', {})
        elif command == 'users':
            self._execute_tool('get_all_users', {})
        elif command == 'user-info':
            if not args:
                print("❌ Uso: user-info <usuario>")
                return
            self._execute_tool('get_user_full_info', {'username': args})
        elif command == 'groups-all':
            self._execute_tool('get_all_groups', {})
        elif command == 'domain':
            self._execute_tool('get_domain_info', {})
        elif command == 'groups':
            self._execute_tool('get_all_groups', {})
        elif command == 'privilege':
            username = args or self._get_ldap_username()
            self._execute_tool('get_user_memberships_recursive', {'username': username})
        elif command == 'computers':
            self._execute_tool('get_all_computers', {})
        elif command == 'shares':
            self._execute_tool('get_all_shares', {})
        elif command == 'domain-enum-all':
            self._execute_domain_enum_all()
        elif command == 'adcs-templates':
            self._execute_tool('get_adcs_templates', {})
        elif command == 'gpos':
            self._execute_tool('get_gpos', {})
        elif command == 'policies':
            self._execute_tool('get_policies', {})
        elif command == 'spns':
            self._execute_tool('get_spns', {})
        elif command == 'delegation':
            self._execute_tool('get_delegations', {})
        else:
            print(f"❌ Comando desconocido: {command}")
            print("   Escribe 'help' para ver comandos disponibles")
    
    # Mapa de herramientas → descripción corta para sugerencias offline
    _TOOL_HINTS = [
        ('whoami',        'get_current_user_info',             'usuario LDAP actual'),
        ('users',         'get_all_users',                     'todos los usuarios del dominio'),
        ('user-info',     'get_user_full_info',                'todos los atributos de un usuario específico'),
        ('groups',        'get_all_groups',                    'todos los grupos y sus miembros'),
        ('privilege',     'get_user_memberships_recursive',    'grupos directos e heredados de un usuario'),
        ('computers',     'get_all_computers',                 'equipos registrados en el dominio'),
        ('shares',        'get_all_shares',                    'recursos compartidos'),
        ('domain',        'get_domain_info',                   'estructura e info del dominio'),
        ('policies',      'get_policies',                      'políticas de contraseñas y PSOs'),
        ('spns',          'get_spns',                          'cuentas kerberoasteables (SPNs)'),
        ('delegation',    'get_delegations',                   'delegación Kerberos (unconstrained/constrained/RBCD)'),
        ('adcs-templates','get_adcs_templates',                'templates ADCS (ESC1-ESC3)'),
        ('gpos',          'get_gpos',                          'Group Policy Objects'),
    ]

    def _suggest_closest_tools(self, query: str):
        """Muestra las herramientas existentes más relevantes para una query sin API."""
        import unicodedata
        def norm(s):
            s = unicodedata.normalize('NFD', s.lower())
            return ''.join(c for c in s if unicodedata.category(c) != 'Mn')
        q = norm(query)

        # Score: cuántas palabras clave de la herramienta aparecen en la query
        scored = []
        for cmd, fn, desc in self._TOOL_HINTS:
            words = norm(cmd + ' ' + fn + ' ' + desc).split()
            score = sum(1 for w in words if len(w) > 3 and w in q)
            scored.append((score, cmd, desc))

        scored.sort(reverse=True)
        top = [x for x in scored if x[0] > 0][:3] or scored[:3]

        print("   Herramientas existentes más cercanas:")
        for _, cmd, desc in top:
            print(f"   → {cmd:<18} {desc}")
        print()

    def _ask_ai(self, query: str):
        """Pregunta a la IA — intenta herramientas existentes primero, luego genera con Gemini"""
        tool_name = self._get_tool_for_query(query)
        if tool_name:
            print(f"\n✅ Usando herramienta existente: {tool_name}\n")
            self._execute_tool(tool_name, {})
            return

        print("\n⚠️  Esta consulta requiere una herramienta específica.")
        print("🤖 Consultando con IA para crearla...\n")
        try:
            process_result = self.coordinator.process_query(query)
            status = process_result.get('status')

            if status == 'using_existing_tool':
                inferred = self.coordinator._infer_tool(query)
                if inferred:
                    print(f"✅ Herramienta inferida por IA: {inferred}\n")
                    self._execute_tool(inferred, {})
                else:
                    print("⚠️  La IA sugiere una herramienta existente pero no pudo identificarla.\n")
                    self._suggest_closest_tools(query)

            elif status == 'new_tool_generated':
                new_tool = process_result.get('tool_name')
                print(f"✅ Nueva herramienta generada: {new_tool}\n")
                self.coordinator.executor.reload_generated_tools()
                self._execute_tool(new_tool, {})

            elif status == 'generation_failed':
                print(f"❌ No se pudo generar herramienta: {process_result.get('error')}\n")
                self._suggest_closest_tools(query)

            else:
                print(f"⚠️  Respuesta inesperada de la IA: {status}\n")

        except Exception as e:
            err = str(e).lower()
            if any(k in err for k in ['quota', 'resource_exhausted', '429', 'token', 'rate limit', 'insufficient']):
                print("❌ API no disponible (sin tokens o límite alcanzado).\n")
                print("   Para consultas específicas se necesita la API de Gemini.")
                print("   Sin API, solo están disponibles los comandos directos:\n")
                self._suggest_closest_tools(query)
            else:
                print(f"❌ Error en análisis IA: {e}\n")
                self._suggest_closest_tools(query)
    
    def _get_ldap_username(self) -> str:
        """Extrae el username del bind DN del conector LDAP"""
        from ldap_agents.connector import get_ldap_connector
        try:
            bind_dn = get_ldap_connector().bind_dn
            return bind_dn.split(',')[0].split('=')[1]
        except (IndexError, AttributeError):
            return 'admin'

    def _get_tool_for_query(self, query: str) -> str:
        """Determina qué herramienta usar para una pregunta (delega al coordinador)"""
        return self.coordinator._infer_tool(query)
    
    def _execute_tool(self, tool_name: str, params: dict):
        """Ejecuta una herramienta con formato bonito"""
        result = self.coordinator.executor.execute(tool_name, **params)
        
        if not result.get('success'):
            print(f"❌ Error: {result.get('error', 'Error desconocido')}\n")
            return
        
        # El resultado viene directamente sin envoltorio 'data'
        data = result
        print()  # Línea en blanco
        
        # Formato bonito según tipo de dato
        # Nota: 'attributes' se chequea antes que 'groups' porque whoami tiene ambas claves
        if isinstance(data, dict):
            if 'users' in data and isinstance(data['users'], list):
                self._format_users(data)
            elif 'attributes' in data:
                self._format_user_info(data)
            elif 'direct_groups' in data:
                self._format_privilege(data)
            elif 'groups' in data and isinstance(data['groups'], list):
                self._format_groups(data)
            elif 'computers' in data and isinstance(data['computers'], list):
                self._format_computers(data)
            elif 'shares' in data and isinstance(data['shares'], list):
                self._format_shares(data)
            elif 'domain_info' in data:
                self._format_domain(data)
            elif 'total_templates' in data:
                self._format_adcs_templates(data)
            elif 'total_gpos' in data:
                self._format_gpos(data)
            elif 'domain_password_policy' in data:
                self._format_policies(data)
            elif 'total_kerberoastable' in data:
                self._format_spns(data)
            elif 'unconstrained_delegation' in data:
                self._format_delegations(data)
            else:
                print(json.dumps(data, indent=2, default=str))
        else:
            print(json.dumps(data, indent=2, default=str))
        
        print()
    
    def _format_users(self, data):
        """Formato bonito para usuarios"""
        print(f"📊 Usuarios: {data.get('total_users', len(data['users']))} total\n")
        print(f"   Mostrando {len(data['users'])}:")
        for i, user in enumerate(data['users'], 1):
            if isinstance(user, dict):
                uid = user.get('uid', '?')
                mail = user.get('mail', '')
                print(f"   {i:2d}. {uid} ({mail})")
            else:
                print(f"   {i:2d}. {user}")
    
    def _format_groups(self, data):
        """Formato bonito para grupos"""
        print(f"📊 Grupos: {data.get('total_groups', len(data['groups']))} total\n")
        print(f"   Mostrando {len(data['groups'])}:")
        for i, group in enumerate(data['groups'], 1):
            if isinstance(group, dict):
                cn = group.get('cn', '?')
                members = group.get('member_count', '?')
                print(f"   {i:2d}. {cn} ({members} miembros)")
            else:
                print(f"   {i:2d}. {group}")
        
        if data.get('sensitive_groups'):
            print(f"\n   🚨 Grupos sensibles: {', '.join(data['sensitive_groups'])}")
    
    def _format_computers(self, data):
        """Formato bonito para computadoras"""
        print(f"🖥️  Computadoras: {data.get('total_computers', len(data['computers']))} total\n")
        print(f"   Mostrando {len(data['computers'])}:")
        for i, computer in enumerate(data['computers'], 1):
            print(f"   {i:2d}. {computer}")
    
    def _format_shares(self, data):
        """Formato bonito para shares"""
        print(f"📂 Shares: {data.get('total_shares', len(data['shares']))} total\n")
        print(f"   Mostrando {len(data['shares'])}:")
        for i, share in enumerate(data['shares'], 1):
            print(f"   {i:2d}. {share}")
    
    def _format_domain(self, data):
        """Formato bonito para info del dominio"""
        domain_info = data.get('domain_info', {})
        print(f"📍 Información del Dominio\n")
        print(f"   Base DN: {domain_info.get('base_dn', 'N/A')}")
        print(f"   Servidor: {domain_info.get('server', 'N/A')}")
        
        if isinstance(domain_info, dict):
            domain_info_list = domain_info.get('domain_info', [])
            if domain_info_list and len(domain_info_list) > 0:
                first = domain_info_list[0]
                if isinstance(first, dict):
                    org = first.get('o', ['N/A'])[0] if isinstance(first.get('o'), list) else first.get('o', 'N/A')
                    dc = first.get('dc', ['N/A'])[0] if isinstance(first.get('dc'), list) else first.get('dc', 'N/A')
                    print(f"   Organización: {org}")
                    print(f"   Dominio: {dc}")
    
    def _format_user_info(self, data):
        """Formato bonito para información completa del usuario"""
        attrs = data.get('attributes', {})
        username = data.get('username', '?')
        
        print(f"👤 Usuario: {username}\n")
        
        # Campos importantes primero
        important_fields = ['uid', 'cn', 'mail', 'pager', 'phone', 'description']
        
        for key in important_fields:
            if key in attrs:
                value = attrs[key]
                display_key = key.replace('_', ' ').title()
                
                if isinstance(value, list):
                    if value:
                        for v in value:
                            if isinstance(v, bytes):
                                v = v.decode('utf-8')
                            print(f"   {display_key}: {v}")
                    else:
                        print(f"   {display_key}: (vacío)")
                else:
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    print(f"   {display_key}: {value}")
        
        # Otros campos
        print()
        for key, value in attrs.items():
            if key not in important_fields:
                display_key = key.replace('_', ' ').title()

                if isinstance(value, list):
                    if value:
                        first = value[0]
                        if isinstance(first, bytes):
                            first = first.decode('utf-8')
                        print(f"   {display_key}: {first}")
                        if len(value) > 1:
                            print(f"      (y {len(value)-1} más)")
                else:
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    print(f"   {display_key}: {value}")

        # Grupos (presentes cuando viene de whoami)
        groups = data.get('groups')
        if groups:
            print(f"\n   Grupos: {', '.join(groups)}")

    def _format_privilege(self, data):
        """Formato bonito para análisis de privilegios"""
        username = data.get('username', '?')
        direct = data.get('direct_groups', [])
        nested = data.get('nested_groups', [])
        risky = data.get('risky_groups', [])
        total = data.get('total_effective_groups', len(set(direct) | set(nested)))
        escalation = data.get('privilege_escalation_potential', False)

        print(f"🔐 Análisis de Privilegios: {username}\n")
        print(f"   Grupos directos ({len(direct)}):")
        for g in direct:
            print(f"      • {g}")

        only_nested = [g for g in nested if g not in direct]
        if only_nested:
            print(f"\n   Grupos heredados ({len(only_nested)}):")
            for g in only_nested:
                print(f"      • {g}")

        print(f"\n   Total grupos efectivos: {total}")

        if risky:
            print(f"\n   🚨 Grupos de riesgo: {', '.join(risky)}")
            print(f"   ⚡ Potencial de escalada: {'SÍ' if escalation else 'NO'}")
        else:
            print(f"\n   ✅ Sin grupos de alto riesgo detectados")

    def _format_adcs_templates(self, data):
        """Formato bonito para ADCS templates"""
        total = data.get('total_templates', 0)
        vulnerable = data.get('potentially_vulnerable', [])
        print(f"🔏 ADCS Templates: {total} encontrados\n")
        if data.get('note'):
            print(f"   ℹ️  {data['note']}\n")
        if vulnerable:
            print(f"   🚨 Potencialmente vulnerables ({len(vulnerable)}):")
            for t in vulnerable:
                flags = ', '.join(k for k, v in t.get('flags', {}).items() if v)
                print(f"      • {t['cn']}  [{flags}]")
        elif total > 0:
            print(f"   ✅ Sin misconfiguraciones ESC detectadas automáticamente")
            print(f"   ⚠️  Revisar manualmente permisos de enrolamiento (ESC4/ESC5)")
        else:
            print("   ℹ️  No se encontraron templates (entorno sin ADCS o OpenLDAP puro)")

    def _format_gpos(self, data):
        """Formato bonito para GPOs"""
        total = data.get('total_gpos', 0)
        gpos = data.get('gpos', [])
        print(f"📋 Group Policy Objects: {total} encontradas\n")
        if data.get('note'):
            print(f"   ℹ️  {data['note']}\n")
        if gpos:
            for i, gpo in enumerate(gpos, 1):
                print(f"   {i:2d}. {gpo.get('name', '?')}")
                if gpo.get('sysvol_path') and gpo['sysvol_path'] != 'N/A':
                    print(f"       └─ {gpo['sysvol_path']}")
        else:
            print("   ℹ️  Sin GPOs encontradas (entorno sin GPOs o OpenLDAP puro)")

    def _format_policies(self, data):
        """Formato bonito para políticas de contraseñas"""
        pol = data.get('domain_password_policy', {})
        psos = data.get('fine_grained_policies', [])
        spray_threshold = data.get('spray_safe_threshold')

        print(f"🔑 Políticas de Contraseñas del Dominio\n")

        fields = [
            ('Longitud mínima', 'pwd_min_length'),
            ('Historial contraseñas', 'pwd_history_length'),
            ('Edad máxima (días)', 'pwd_max_age_days'),
            ('Umbral de lockout', 'lockout_threshold'),
            ('Duración lockout (min)', 'lockout_duration_mins'),
        ]
        any_val = False
        for label, key in fields:
            val = pol.get(key)
            if val is not None:
                print(f"   {label}: {val}")
                any_val = True

        if not any_val:
            print("   ℹ️  Sin atributos de política encontrados (puede requerir permisos adicionales)")

        if spray_threshold:
            try:
                threshold = int(spray_threshold)
                safe = max(0, threshold - 2)
                print(f"\n   ⚡ Password Spray: mantener < {safe} intentos por cuenta para no triggear lockout")
            except (ValueError, TypeError):
                pass

        if psos:
            print(f"\n   Fine-Grained Policies (PSOs): {len(psos)}")
            for pso in psos:
                print(f"      • {pso.get('cn', '?')}")
        else:
            print("\n   ℹ️  Sin Fine-Grained Password Policies (PSOs)")

    def _format_spns(self, data):
        """Formato bonito para SPNs (Kerberoasting)"""
        total = data.get('total_kerberoastable', 0)
        accounts = data.get('accounts', [])
        print(f"🎫 Cuentas Kerberoasteables (SPNs): {total}\n")
        if accounts:
            for i, acc in enumerate(accounts, 1):
                print(f"   {i:2d}. {acc['account']}  ({acc['spn_count']} SPN{'s' if acc['spn_count'] != 1 else ''})")
                for spn in acc.get('spns', [])[:3]:
                    print(f"       └─ {spn}")
                if len(acc.get('spns', [])) > 3:
                    print(f"       └─ ... y {len(acc['spns'])-3} más")
            print(f"\n   ⚡ {data.get('attack_note', '')}")
        else:
            print("   ✅ No se encontraron cuentas con SPNs")

    def _format_delegations(self, data):
        """Formato bonito para delegación Kerberos"""
        unconstrained = data.get('unconstrained_delegation', [])
        constrained = data.get('constrained_delegation', [])
        rbcd = data.get('resource_based_delegation', [])

        print(f"🔄 Delegación Kerberos\n")

        if unconstrained:
            print(f"   🚨 UNCONSTRAINED ({len(unconstrained)}) — Alto riesgo:")
            for e in unconstrained:
                print(f"      • {e['account']}")
        else:
            print("   ✅ Unconstrained: ninguna")

        if constrained:
            print(f"\n   ⚠️  CONSTRAINED ({len(constrained)}):")
            for e in constrained:
                targets = e.get('delegates_to', [])
                print(f"      • {e['account']} → {', '.join(targets[:2]) if targets else 'N/A'}")
        else:
            print("   ✅ Constrained: ninguna")

        if rbcd:
            print(f"\n   ⚠️  RESOURCE-BASED ({len(rbcd)}):")
            for e in rbcd:
                print(f"      • {e['account']}")
        else:
            print("   ✅ RBCD: ninguna")

        if data.get('attack_note') and (unconstrained or constrained):
            print(f"\n   ⚡ {data['attack_note']}")

    def _execute_domain_enum_all(self):
        """Enumeración completa del dominio: todos los módulos"""
        modules = [
            ("🌐 Dominio",           'get_domain_info',      {}),
            ("👥 Usuarios",          'get_all_users',         {}),
            ("📁 Grupos",            'get_all_groups',         {}),
            ("🔑 Políticas",         'get_policies',           {}),
            ("🎫 SPNs",              'get_spns',               {}),
            ("🔄 Delegación",        'get_delegations',        {}),
            ("🖥️  Computadoras",     'get_all_computers',      {}),
            ("📂 Shares",            'get_all_shares',         {}),
            ("🔏 ADCS Templates",    'get_adcs_templates',     {}),
            ("📋 GPOs",              'get_gpos',               {}),
        ]

        print("\n" + "="*80)
        print("  🌐 DOMAIN ENUM ALL — Enumeración Completa")
        print("="*80)

        for label, tool, params in modules:
            print(f"\n{'─'*40}")
            print(f"  {label}")
            print('─'*40)
            self._execute_tool(tool, params)

    def _show_generated_tools(self):
        """Muestra herramientas generadas"""
        generated = self.coordinator.get_status()['generated_tools']
        if generated:
            print(f"\n✨ Herramientas Generadas ({len(generated)}):")
            for tool in generated:
                print(f"   • {tool}\n")
        else:
            print("\n🤖 No hay herramientas generadas aún\n")
    
    def _show_status(self):
        """Muestra estado del sistema"""
        status = self.coordinator.get_status()
        
        print("\n" + "="*80)
        print("  📊 ESTADO DEL SISTEMA")
        print("="*80 + "\n")
        
        print(f"  Herramientas disponibles: {len(status['executor_tools'])}")
        print(f"  Herramientas generadas: {len(status['generated_tools'])}")
        print(f"  Histórico de ejecuciones: {status['execution_history_size']}\n")
    
    def _confirm_reset(self):
        """Resetear el sistema"""
        print("\n⚠️  Esto restaurará el sistema a su estado original.")
        print("   Se eliminarán todas las herramientas generadas.")
        
        response = input("\n¿Estás seguro? (y/n): ").strip().lower()
        
        if response == 'y':
            result = self.coordinator.reset_system()
            print(f"\n✅ {result['message']}\n")
        else:
            print("❌ Reset cancelado\n")
    
    def _show_persistence_info(self):
        """Muestra información de persistencia"""
        from ldap_agents.persistence import get_tool_registry
        
        registry = get_tool_registry()
        info = registry.get_registry_info()
        
        print("\n" + "="*80)
        print("  💾 INFORMACIÓN DE PERSISTENCIA")
        print("="*80 + "\n")
        
        print(f"  Archivo: {info['file']}")
        print(f"  Herramientas almacenadas: {info['total_tools']}\n")
    
    def run(self):
        """Inicia el CLI"""
        self.print_banner()
        
        while self.running:
            try:
                user_input = input(">>> ").strip()
                
                if user_input:
                    self.execute_command(user_input)
            
            except KeyboardInterrupt:
                print("\n\n🚀 See you, Space Cowboy...\n")
                self.running = False
            except Exception as e:
                print(f"❌ Error: {e}\n")


def main():
    """Función principal"""
    cli = ADInspectorCLI()
    cli.run()


if __name__ == "__main__":
    main()
