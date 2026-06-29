"""
Sistema multi-agente LDAP Auto-Adaptativo
- Coordinador Central: Orquesta y analiza intents
- Agente Ejecutor: Ejecuta herramientas y responde
- Agente Generador: Crea nuevas herramientas automáticamente
"""
import json
import hashlib
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from loguru import logger
import inspect

from .tools import get_tools_registry, call_tool, tool_exists, ALL_TOOLS
from .persistence import get_tool_registry
from .connector import get_ldap_connector


class BaseAgent(ABC):
    """Clase base para todos los agentes"""
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logger
        self.execution_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    def execute(self, task: str, **context) -> Dict[str, Any]:
        """Ejecuta la tarea del agente"""
        pass
    
    def log_execution(self, task: str, result: Dict[str, Any]) -> None:
        """Registra ejecución en historial"""
        self.execution_history.append({
            "task": task,
            "result": result,
            "timestamp": str(__import__('datetime').datetime.now())
        })


class ExecutorAgent(BaseAgent):
    """
    Agente Ejecutor: Ejecuta herramientas disponibles y responde consultas
    """
    
    def __init__(self):
        super().__init__("ExecutorAgent")
        self.available_tools = get_tools_registry()
        self.registry = get_tool_registry()
        self.loaded_generated_tools: Dict[str, Callable] = {}
        self._load_generated_tools()
    
    def _load_generated_tools(self) -> None:
        """Carga herramientas auto-generadas del registro"""
        try:
            tool_names = self.registry.list_tools()
            for tool_name in tool_names:
                tool_data = self.registry.get_tool(tool_name)
                if tool_data and tool_data.get('status') == 'active':
                    try:
                        # Verificar integridad del código antes de ejecutar
                        stored_hash = tool_data.get('code_hash')
                        if stored_hash:
                            actual_hash = hashlib.sha256(tool_data['code'].encode()).hexdigest()
                            if actual_hash != stored_hash:
                                logger.error(f"❌ Hash inválido para '{tool_name}' — herramienta ignorada")
                                continue

                        # Ejecutar código en namespace seguro
                        namespace = {
                            'get_ldap_connector': get_ldap_connector,
                            'logger': logger,
                            'Dict': Dict,
                            'Any': Any,
                            'List': List
                        }
                        exec(tool_data['code'], namespace)
                        
                        # Buscar la función definida en el código
                        for key, value in namespace.items():
                            if callable(value) and key == tool_name:
                                self.loaded_generated_tools[tool_name] = value
                                logger.info(f"✅ Herramienta generada cargada: {tool_name}")
                                break
                    except Exception as e:
                        logger.error(f"❌ Error cargando herramienta generada {tool_name}: {e}")
        except Exception as e:
            logger.error(f"❌ Error en _load_generated_tools: {e}")
    
    def has_tool(self, tool_name: str) -> bool:
        """Verifica si dispone de una herramienta"""
        return tool_exists(tool_name) or tool_name in self.loaded_generated_tools
    
    def get_available_tools(self) -> Dict[str, str]:
        """Retorna descripción de herramientas disponibles"""
        tools_desc = {}
        
        # Herramientas base
        for name, info in self.available_tools.items():
            tools_desc[name] = info['description']
        
        # Herramientas generadas
        for name in self.loaded_generated_tools.keys():
            tool_data = self.registry.get_tool(name)
            if tool_data:
                tools_desc[name] = tool_data.get('metadata', {}).get('description', 'Sin descripción')
        
        return tools_desc
    
    def execute(self, tool_name: str, **params) -> Dict[str, Any]:
        """
        Ejecuta una herramienta específica
        
        Args:
            tool_name: Nombre de la herramienta
            **params: Parámetros para la herramienta
        
        Returns:
            Resultado de la ejecución
        """
        if not self.has_tool(tool_name):
            return {
                "success": False,
                "error": f"Herramienta no disponible: {tool_name}",
                "available_tools": list(self.get_available_tools().keys())
            }
        
        try:
            # Ejecutar herramienta base o generada
            if tool_exists(tool_name):
                result = call_tool(tool_name, **params)
            elif tool_name in self.loaded_generated_tools:
                func = self.loaded_generated_tools[tool_name]
                result = func(**params)
            else:
                result = {"success": False, "error": "Herramienta no encontrada"}
            
            self.log_execution(tool_name, result)
            return result
            
        except TypeError as e:
            return {
                "success": False,
                "error": f"Parámetros incorrectos: {e}",
                "expected_params": self._get_tool_params(tool_name)
            }
        except Exception as e:
            logger.error(f"❌ Error ejecutando {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_tool_params(self, tool_name: str) -> Dict[str, str]:
        """Obtiene parámetros esperados de una herramienta"""
        if tool_name in self.available_tools:
            return self.available_tools[tool_name].get('params', {})
        elif tool_name in self.loaded_generated_tools:
            func = self.loaded_generated_tools[tool_name]
            sig = inspect.signature(func)
            return {name: str(param.annotation) for name, param in sig.parameters.items()}
        return {}
    
    def reload_generated_tools(self) -> None:
        """Recarga las herramientas generadas"""
        self.loaded_generated_tools = {}
        self._load_generated_tools()
        logger.info("🔄 Herramientas generadas recargadas")


class GeneratorAgent(BaseAgent):
    """
    Agente Generador: Crea nuevas herramientas automáticamente
    Utiliza Gemini para generar código Python funcional
    """
    
    def __init__(self, ai_config=None):
        super().__init__("GeneratorAgent")
        self.ai_config = ai_config or self._get_ai_config()
        self.registry = get_tool_registry()
        self.executor = None  # Referencia al agente ejecutor
        self._init_gemini()
    
    def _get_ai_config(self):
        """Obtiene configuración de IA"""
        from .config import ai_config
        return ai_config
    
    def _init_gemini(self) -> None:
        """Inicializa cliente de Gemini"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.ai_config.gemini_api_key)
            self.model = genai.GenerativeModel(self.ai_config.model)
            logger.info("✅ Gemini inicializado correctamente")
        except Exception as e:
            logger.error(f"❌ Error inicializando Gemini: {e}")
            self.model = None
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analiza una consulta para determinar si necesita nueva herramienta
        
        Returns:
            {
                'needs_new_tool': bool,
                'tool_name': str,
                'reason': str,
                'suggested_description': str
            }
        """
        if not self.model:
            return {
                'needs_new_tool': False,
                'error': 'Gemini no disponible'
            }
        
        available_tools = list(self.executor.get_available_tools().keys()) if self.executor else []
        
        prompt = f"""
Analiza esta consulta: "{query}"

Herramientas disponibles:
{', '.join(available_tools)}

¿Se puede responder con herramientas existentes? Si no, ¿qué herramienta nueva se necesita?

Responde en JSON:
{{
    "needs_new_tool": bool,
    "tool_name": "nombre_sugerido" or null,
    "reason": "explicación",
    "suggested_description": "descripción de la herramienta" or null
}}
"""
        try:
            response = self.model.generate_content(prompt)
            text = response.text
            
            # Extraer JSON de la respuesta
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            else:
                return {'needs_new_tool': False, 'reason': 'No se pudo parsear respuesta'}
        except Exception as e:
            logger.error(f"❌ Error analizando query: {e}")
            return {'needs_new_tool': False, 'error': str(e)}
    
    def generate_tool(self, tool_name: str, description: str, 
                     query: str = None) -> Dict[str, Any]:
        """
        Genera código para una nueva herramienta usando Gemini
        
        Args:
            tool_name: Nombre de la herramienta
            description: Descripción de qué debe hacer
            query: Consulta del usuario que originó la generación
        
        Returns:
            Código Python generado y estatus
        """
        if not self.model:
            return {
                'success': False,
                'error': 'Gemini no disponible'
            }
        
        prompt = f"""
Eres un experto en Python y LDAP. Genera una función Python para la siguiente herramienta:

NOMBRE: {tool_name}
DESCRIPCIÓN: {description}
CONTEXTO: Consulta del usuario: "{query}" si aplica

REQUISITOS:
1. Función debe ser named "{tool_name}"
2. Debe usar get_ldap_connector() para acceder a LDAP
3. Parámetros deben ser simples tipos (str, int, bool)
4. Retorna Dict[str, Any]
5. Incluye manejo de errores
6. Usa logger para logging
7. Sintaxis Python 3.10+
8. SOLO código, sin explicaciones

Considera:
- Contexto ofensivo (seguridad)
- Reutilizar métodos existentes del connector
- Documentación en docstring

CÓDIGO (solo función):
"""
        try:
            response = self.model.generate_content(prompt)
            code = response.text.strip()
            
            # Validar código
            validation = self._validate_code(code, tool_name)
            if not validation['valid']:
                return {
                    'success': False,
                    'error': f"Código inválido: {validation['error']}"
                }
            
            # Registrar herramienta
            self.registry.register_tool(
                tool_name,
                code,
                {
                    'description': description,
                    'generated_at': __import__('datetime').datetime.now().isoformat(),
                    'generator': 'GeneratorAgent',
                    'source_query': query
                }
            )
            
            logger.info(f"✅ Herramienta generada: {tool_name}")
            
            return {
                'success': True,
                'tool_name': tool_name,
                'code': code,
                'registered': True
            }
            
        except Exception as e:
            logger.error(f"❌ Error generando herramienta: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _validate_code(self, code: str, tool_name: str) -> Dict[str, Any]:
        """Valida sintaxis del código generado"""
        try:
            compile(code, '<string>', 'exec')
            
            # Verificar que la función existe
            if f"def {tool_name}" not in code:
                return {
                    'valid': False,
                    'error': f'Función {tool_name} no encontrada en código'
                }
            
            return {'valid': True}
        except SyntaxError as e:
            return {
                'valid': False,
                'error': f'Error de sintaxis: {e}'
            }
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
    
    def execute(self, task: str, **context) -> Dict[str, Any]:
        """Interfaz genérica para ejecutar tareas del generador"""
        if task == 'analyze':
            return self.analyze_query(context.get('query', ''))
        elif task == 'generate':
            return self.generate_tool(
                context.get('tool_name'),
                context.get('description'),
                context.get('query')
            )
        else:
            return {'success': False, 'error': f'Tarea desconocida: {task}'}


class Coordinator(BaseAgent):
    """
    Coordinador Central: Orquesta la interacción entre agentes
    Maneja el flujo principal de consultas
    """
    
    def __init__(self):
        super().__init__("Coordinator")
        self.executor = ExecutorAgent()
        self.generator = GeneratorAgent()
        self.generator.executor = self.executor  # Referencia circular necesaria
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Procesa una consulta del usuario
        
        Flujo:
        1. Analizar si el ejecutor puede responder
        2. Si no: generar nueva herramienta
        3. Recargar ejecutor
        4. Ejecutar y responder
        """
        logger.info(f"📥 Procesando query: {query}")
        
        # Paso 1: Analizar
        analysis = self.generator.analyze_query(query)
        
        if not analysis.get('needs_new_tool'):
            logger.info("✅ Herramienta existente puede responder")
            return {
                "status": "using_existing_tool",
                "analysis": analysis,
                "next_step": "Usar herramienta existente"
            }
        
        # Paso 2: Generar nueva herramienta
        logger.info(f"🔄 Generando nueva herramienta: {analysis.get('tool_name')}")
        
        generation_result = self.generator.generate_tool(
            tool_name=analysis.get('tool_name'),
            description=analysis.get('suggested_description'),
            query=query
        )
        
        if not generation_result.get('success'):
            return {
                "status": "generation_failed",
                "error": generation_result.get('error'),
                "suggestion": "Intenta con herramientas existentes"
            }
        
        # Paso 3: Recargar ejecutor
        logger.info("🔄 Recargando ejecutor con nueva herramienta")
        self.executor.reload_generated_tools()
        
        return {
            "status": "new_tool_generated",
            "tool_name": analysis.get('tool_name'),
            "generation_success": True,
            "next_step": "Ejecutar con nueva herramienta"
        }
    
    def execute_query(self, query: str, tool_name: str = None, 
                     tool_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Ejecuta una consulta con una herramienta específica
        
        Args:
            query: Consulta del usuario
            tool_name: Nombre de la herramienta (auto-detectado si no se proporciona)
            tool_params: Parámetros para la herramienta
        """
        logger.info(f"⚙️  Ejecutando query: {query}")
        
        if not tool_name:
            tool_name = self._infer_tool(query)
        
        if not tool_name:
            return {
                "success": False,
                "error": "No se pudo inferir herramienta para la consulta",
                "available_tools": list(self.executor.get_available_tools().keys())
            }
        
        tool_params = tool_params or {}
        
        # Ejecutar
        result = self.executor.execute(tool_name, **tool_params)
        
        return {
            "success": result.get('success', False),
            "query": query,
            "tool_used": tool_name,
            "result": result
        }
    
    # Palabras que indican filtrado/especificidad — la query necesita más que una herramienta genérica
    FILTER_QUALIFIERS = [
        'con ', 'donde ', 'que tengan', 'que sean', 'que esten', 'que tienen',
        'filtrar', 'buscar por', 'encontrar', 'buscar usuarios', 'buscar grupos',
        'descripcion', 'atributo', 'campo', 'valor', 'contienen', 'cuyo',
        'cuya', 'especifico', 'solo los', 'unicamente', 'contractor', 'sin ',
        'habilitados', 'deshabilitados', 'bloqueados', 'expirados', 'inactivos',
        'creados', 'modificados', 'pertenecen', 'no pertenecen',
    ]

    def _infer_tool(self, query: str) -> Optional[str]:
        """Infiere herramienta basada en la consulta.

        Retorna None si la query tiene calificadores de filtro — indica que ninguna
        herramienta genérica puede responderla correctamente y debe ir a Gemini.
        """
        import unicodedata

        def norm(s):
            s = unicodedata.normalize('NFD', s.lower())
            return ''.join(c for c in s if unicodedata.category(c) != 'Mn')

        query_lower = norm(query)

        # Si la query tiene calificadores de filtro, no intentar match genérico
        if any(norm(q) in query_lower for q in self.FILTER_QUALIFIERS):
            return None

        keyword_tools = [
            (['quien soy', 'whoami', 'usuario actual', ' yo ', 'actual'], 'get_current_user_info'),
            (['todos los usuarios', 'enumerar usuario', 'listar usuario', 'usuarios', 'users'], 'get_all_users'),
            (['todos los grupos', 'groups-all', 'grupos-all', 'listar grupos', 'grupos', 'groups'], 'get_all_groups'),
            (['dominio', 'domain', 'estructura del directorio', 'informacion del dominio'], 'get_domain_info'),
            (['privilegios', 'privilege', 'escalada', 'membresias', 'memberships', 'permisos heredados'], 'get_user_memberships_recursive'),
            (['computadoras', 'computers', 'equipos', 'hosts', 'maquinas'], 'get_all_computers'),
            (['shares', 'compartidos', 'recursos compartidos'], 'get_all_shares'),
            (['adcs', 'certificate template', 'esc1', 'esc2', 'esc3', 'certificados'], 'get_adcs_templates'),
            (['gpo', 'group policy', 'politicas de grupo', 'policy object'], 'get_gpos'),
            (['password policy', 'politica de contrasena', 'lockout', 'spray', 'contrasenas del dominio'], 'get_policies'),
            (['spn', 'kerberoast', 'service principal', 'ticket tgs', 'cuentas de servicio'], 'get_spns'),
            (['delegacion', 'delegation', 'unconstrained', 'constrained', 'rbcd', 'kerberos delegation'], 'get_delegations'),
        ]

        for keywords, tool in keyword_tools:
            if any(norm(kw) in query_lower for kw in keywords):
                return tool

        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna estado del sistema"""
        return {
            "coordinator": self.name,
            "executor_tools": list(self.executor.get_available_tools().keys()),
            "generated_tools": get_tool_registry().list_tools(),
            "execution_history_size": len(self.execution_history),
            "registry_info": get_tool_registry().get_registry_info()
        }
    
    def reset_system(self) -> Dict[str, Any]:
        """Restaura el sistema a su estado original"""
        logger.info("♻️  Reseteando sistema a estado original")
        
        get_tool_registry().reset_to_defaults()
        self.executor.reload_generated_tools()
        self.execution_history = []
        
        return {
            "success": True,
            "message": "Sistema restaurado a estado original",
            "status": self.get_status()
        }
    
    def execute(self, task: str, **context) -> Dict[str, Any]:
        """Interfaz genérica para coordinador"""
        if task == 'process_query':
            return self.process_query(context.get('query', ''))
        elif task == 'execute_query':
            return self.execute_query(
                context.get('query'),
                context.get('tool_name'),
                context.get('tool_params')
            )
        elif task == 'status':
            return self.get_status()
        elif task == 'reset':
            return self.reset_system()
        else:
            return {'success': False, 'error': f'Tarea desconocida: {task}'}
