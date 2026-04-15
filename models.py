"""
Modelos de dados do sistema
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional
import uuid


@dataclass
class Paciente:
    """Modelo de paciente completo"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nome: str = ""
    data_nascimento: str = ""
    sexo: str = ""
    cpf: str = ""
    rg: str = ""
    estado_civil: str = ""
    tipo_sanguineo: str = ""
    
    telefone: str = ""
    celular: str = ""
    email: str = ""
    whatsapp: str = ""
    
    cep: str = ""
    endereco: str = ""
    numero: str = ""
    complemento: str = ""
    bairro: str = ""
    cidade: str = ""
    estado: str = ""
    pais: str = "Brasil"
    
    contato_emergencia_nome: str = ""
    contato_emergencia_telefone: str = ""
    contato_emergencia_parentesco: str = ""
    
    alergias: List[str] = field(default_factory=list)
    medicamentos_uso: List[str] = field(default_factory=list)
    doencas_cronicas: List[str] = field(default_factory=list)
    cirurgias_previas: List[str] = field(default_factory=list)
    historico_familiar: Dict[str, str] = field(default_factory=dict)
    observacoes: str = ""
    
    data_cadastro: str = field(default_factory=lambda: datetime.now().isoformat())
    data_atualizacao: str = field(default_factory=lambda: datetime.now().isoformat())
    ativo: bool = True

    @classmethod
    def criar_novo(cls, **kwargs) -> 'Paciente':
        campos_validos = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        return cls(**campos_validos)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Paciente':
        return cls(**data)
    
    def get_nome_completo(self) -> str:
        return self.nome
    
    def get_idade(self) -> int:
        from utils import calcular_idade
        return calcular_idade(self.data_nascimento)


@dataclass
class Diagnostico:
    """Modelo de diagnóstico"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    paciente_id: str = ""
    paciente_nome: str = ""
    sintomas: List[str] = field(default_factory=list)
    data_hora: str = field(default_factory=lambda: datetime.now().isoformat())
    resultados: List[Dict] = field(default_factory=list)
    top_resultado: str = ""
    top_porcentagem: float = 0.0

    @classmethod
    def criar_novo(cls, paciente: 'Paciente', sintomas: List[str],
                   resultados: List[Dict]) -> 'Diagnostico':
        if resultados:
            top_resultado = resultados[0].get('doenca', 'N/A')
            top_porcentagem = resultados[0].get('porcentagem', 0.0)
        else:
            top_resultado = "Nenhum resultado"
            top_porcentagem = 0.0

        return cls(
            paciente_id=paciente.id,
            paciente_nome=paciente.nome,
            sintomas=sintomas,
            resultados=resultados[:10],
            top_resultado=top_resultado,
            top_porcentagem=top_porcentagem
        )


@dataclass
class Doenca:
    """Modelo de doença"""
    nome: str = ""
    tipo: str = "físico"
    categoria: str = "fisica"
    descricao: str = ""
    tratamento: str = ""
    severidade: str = "moderada"
    sintomas: List[Dict] = field(default_factory=list)
    condicoes: Dict = field(default_factory=dict)
    
    _sintomas_nomes: set = field(default_factory=set, repr=False, compare=False)
    _obrigatorios: set = field(default_factory=set, repr=False, compare=False)
    _min_sintomas: int = 0

    @classmethod
    def from_dict(cls, data: Dict) -> 'Doenca':
        return cls(
            nome=data.get('doenca', ''),
            tipo=data.get('tipo', 'físico'),
            categoria=data.get('categoria', 'fisica'),
            descricao=data.get('descricao', ''),
            tratamento=data.get('tratamento', ''),
            severidade=data.get('severidade', 'moderada'),
            sintomas=data.get('sintomas', []),
            condicoes=data.get('condicoes', {})
        )