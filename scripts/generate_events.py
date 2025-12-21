import yaml
from pathlib import Path
import json

def load_openapi_schemas(openapi_path):
    with open(openapi_path) as f:
        openapi = yaml.safe_load(f)
    return openapi.get('components', {}).get('schemas', {})

def resolve_schema(schema_ref, openapi_schemas):
    """Resolve a schema reference or return inline schema"""
    if isinstance(schema_ref, str):
        # It's a reference to OpenAPI schema
        return openapi_schemas.get(schema_ref, {})
    elif isinstance(schema_ref, dict):
        # It's an inline schema, may contain $ref
        resolved = {}
        for key, value in schema_ref.items():
            if key == 'properties':
                resolved[key] = {}
                for prop_name, prop_value in value.items():
                    if isinstance(prop_value, dict) and '$ref' in prop_value:
                        ref_name = prop_value['$ref']
                        resolved[key][prop_name] = openapi_schemas.get(ref_name, prop_value)
                    else:
                        resolved[key][prop_name] = prop_value
            else:
                resolved[key] = value
        return resolved
    return schema_ref

def openapi_type_to_ts(prop_schema):
    """Convert OpenAPI type to TypeScript type"""
    prop_type = prop_schema.get('type', 'any')
    
    if prop_type == 'string':
        if 'enum' in prop_schema:
            return ' | '.join(f"'{e}'" for e in prop_schema['enum'])
        return 'string'
    elif prop_type == 'integer' or prop_type == 'number':
        return 'number'
    elif prop_type == 'boolean':
        return 'boolean'
    elif prop_type == 'array':
        items = prop_schema.get('items', {})
        item_type = openapi_type_to_ts(items)
        return f'{item_type}[]'
    elif prop_type == 'object':
        return 'any'  # Could be expanded to handle nested objects
    return 'any'

def openapi_type_to_python(prop_schema):
    """Convert OpenAPI type to Python type"""
    prop_type = prop_schema.get('type', 'Any')
    
    if prop_type == 'string':
        return 'str'
    elif prop_type == 'integer':
        return 'int'
    elif prop_type == 'number':
        return 'float'
    elif prop_type == 'boolean':
        return 'bool'
    elif prop_type == 'array':
        items = prop_schema.get('items', {})
        item_type = openapi_type_to_python(items)
        return f'List[{item_type}]'
    elif prop_type == 'object':
        return 'dict'
    return 'Any'

def to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def to_pascal_case(snake_str):
    return ''.join(x.title() for x in snake_str.split('_'))

def generate_typescript_client(events, openapi_schemas, output_path):
    """Generate TypeScript client with OpenAPI schema integration"""
    
    # Generate types from both server_to_client and client_to_server
    types = []
    all_events = {**events['server_to_client'], **events['client_to_server']}
    
    for event_name, event_data in all_events.items():
        type_name = to_pascal_case(event_name) + 'Payload'
        schema = resolve_schema(event_data, openapi_schemas)
        
        if 'properties' in schema:
            fields = []
            required = schema.get('required', [])
            for field, field_schema in schema['properties'].items():
                ts_type = openapi_type_to_ts(field_schema)
                optional = '' if field in required else '?'
                fields.append(f"  {field}{optional}: {ts_type};")
            
            types.append(f"export interface {type_name} {{\n" + "\n".join(fields) + "\n}\n")
    
    # Generate emit functions
    emit_funcs = []
    for event_name in events['client_to_server'].keys():
        func_name = to_camel_case(event_name)
        type_name = to_pascal_case(event_name) + 'Payload'
        
        emit_funcs.append(f"""  {func_name}(payload: {type_name}) {{
    this.socket.emit('{event_name}', payload);
  }}""")
    
    # Generate listener functions
    listener_funcs = []
    for event_name in events['server_to_client'].keys():
        func_name = 'on' + to_pascal_case(event_name)
        type_name = to_pascal_case(event_name) + 'Payload'
        
        listener_funcs.append(f"""  {func_name}(callback: (payload: {type_name}) => void) {{
    this.socket.on('{event_name}', callback);
    return () => this.socket.off('{event_name}', callback);
  }}""")
    
    output = f"""// Auto-generated - DO NOT EDIT
import {{ Socket }} from 'socket.io-client';

{chr(10).join(types)}

export class SocketIOClient {{
  private socket: Socket;

  constructor(socket: Socket) {{
    this.socket = socket;
  }}

{chr(10).join(emit_funcs)}

{chr(10).join(listener_funcs)}
}}
"""
    
    Path(output_path).write_text(output)
    print(f"Generated TypeScript client: {output_path}")


def generate_server_events(events, openapi_schemas, output_path):
    

def generate_python_server(events, openapi_schemas, output_path):
    """Generate Python server with OpenAPI schema integration"""
    
    # Generate Pydantic models
    models = []
    all_events = {**events['server_to_client'], **events['client_to_server']}
    
    for event_name, event_data in all_events.items():
        class_name = to_pascal_case(event_name) + 'Payload'
        schema = resolve_schema(event_data, openapi_schemas)
        
        if 'properties' in schema:
            fields = []
            required = schema.get('required', [])
            for field, field_schema in schema['properties'].items():
                py_type = openapi_type_to_python(field_schema)
                optional = '' if field in required else ' | None = None'
                fields.append(f"    {field}: {py_type}{optional}")
            
            models.append(f"class {class_name}(BaseModel):\n" + "\n".join(fields) + "\n")
    
    # Generate emit functions
    emit_funcs = []
    for event_name in events['server_to_client'].keys():
        func_name = event_name
        class_name = to_pascal_case(event_name) + 'Payload'
        
        emit_funcs.append(f"""    def {func_name}(self, payload: {class_name}, room: str | None = None):
        data = payload.model_dump()
        if room:
            self.socketio.emit('{event_name}', data, room=room)
        else:
            self.socketio.emit('{event_name}', data)""")
    
    # Generate decorators
    decorator_funcs = []
    for event_name in events['client_to_server'].keys():
        func_name = 'on_' + event_name
        class_name = to_pascal_case(event_name) + 'Payload'
        
        decorator_funcs.append(f"""    def {func_name}(self, handler):
        @self.socketio.on('{event_name}')
        def wrapper(data):
            payload = {class_name}(**data)
            return handler(payload)
        return wrapper""")
    
    output = f"""# Auto-generated - DO NOT EDIT
from pydantic import BaseModel
from typing import Any, List
from flask_socketio import SocketIO

{chr(10).join(models)}

class SocketIOServer:
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
    
{chr(10).join(emit_funcs)}
    
{chr(10).join(decorator_funcs)}
"""
    
    Path(output_path).write_text(output)
    print(f"Generated Python server: {output_path}")

if __name__ == '__main__':
    from pathlib import Path

    path = Path(__file__).parent.parent
    openapi_schemas = load_openapi_schemas(f'{path}/api_types.yaml')
    
    with open(f'{path}/api_events.yaml') as f:
        events = yaml.safe_load(f)
    
    # Generate
    generate_typescript_client(events, openapi_schemas, path / 'client/src/socketio-client.ts')
    generate_python_server(events, openapi_schemas, path / 'backend/socketio_wrapper.py')