"""
Gerenciamento de dados do sistema
"""
import json
import os
import threading
from datetime import datetime
from tkinter import messagebox
from typing import Dict, List, Optional

from config import CONFIG, ConfigManager
from models import Paciente, Diagnostico, Doenca
from utils import setup_logging, BackupManager
from historico import HistoricoManager

logger = setup_logging(CONFIG["LOG_FILE"])


class Database:
    """Gerenciador de banco de dados com índices para buscas rápidas"""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        with self._lock:
            if hasattr(self, '_initialized') and self._initialized:
                return

            self.pacientes_file = ConfigManager.get_path(CONFIG["PACIENTES_FILE"])
            self.sintomas_file = ConfigManager.get_path(CONFIG["JSON_FILE"])

            self.pacientes: Dict[str, Paciente] = {}
            self._indice_cpf: Dict[str, str] = {}
            self._indice_nome: Dict[str, List[str]] = {}

            self.doencas: List[Doenca] = []

            self.backup_manager = BackupManager(
                ConfigManager.get_path("backups"),
                CONFIG["BACKUP_DAYS_TO_KEEP"]
            )

            self.historico_manager = HistoricoManager()
            self._carregar_dados()
            self._initialized = True

    def _carregar_dados(self):
        self._carregar_pacientes()
        self._carregar_doencas()

    def recarregar_doencas(self):
        self.db._carregar_doencas()   # recarrega do JSON
        self.engine.clear_cache()
        self.engine._preprocessar_doencas()
        messagebox.showinfo("Recarregado", "Base de doenças recarregada e cache limpo.")

    def _carregar_pacientes(self):
        try:
            if os.path.exists(self.pacientes_file):
                with open(self.pacientes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.pacientes.clear()
                self._indice_cpf.clear()
                self._indice_nome.clear()

                for pid, p_data in data.items():
                    paciente = Paciente.from_dict(p_data)
                    self.pacientes[pid] = paciente
                    if paciente.cpf:
                        self._indice_cpf[paciente.cpf] = pid
                    nome_key = paciente.nome.lower()
                    self._indice_nome.setdefault(nome_key, []).append(pid)

                logger.info(f"Pacientes carregados: {len(self.pacientes)}")
            else:
                self.pacientes = {}
                logger.info("Arquivo de pacientes não encontrado.")
        except Exception as e:
            logger.error(f"Erro ao carregar pacientes: {e}")
            self.pacientes = {}

    def _carregar_doencas(self):
        try:
            if not os.path.exists(self.sintomas_file):
                logger.error(f"Arquivo {self.sintomas_file} não encontrado")
                return

            with open(self.sintomas_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.doencas = []
            for categoria in ("fisicas", "mentais"):
                if "doencas" in data and categoria in data["doencas"]:
                    for d in data["doencas"][categoria]:
                        try:
                            d = d.copy()
                            d["tipo"] = "físico" if categoria == "fisicas" else "psicológico"
                            d["categoria"] = categoria[:-1]
                            self.doencas.append(Doenca.from_dict(d))
                        except Exception as e:
                            logger.error(f"Erro ao carregar doença: {e}")

            logger.info(f"Doenças carregadas: {len(self.doencas)}")
        except Exception as e:
            logger.error(f"Erro ao carregar doenças: {e}")
            self.doencas = []

    def salvar_pacientes(self) -> bool:
        try:
            self.backup_manager.create_backup(self.pacientes_file, "pacientes")
            data = {pid: p.to_dict() for pid, p in self.pacientes.items()}
            with open(self.pacientes_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar pacientes: {e}")
            return False

    def adicionar_paciente(self, paciente: Paciente) -> bool:
        with self._lock:
            if paciente.cpf and paciente.cpf in self._indice_cpf:
                raise ValueError(f"CPF {paciente.cpf} já cadastrado")
            self.pacientes[paciente.id] = paciente
            if paciente.cpf:
                self._indice_cpf[paciente.cpf] = paciente.id
            nome_key = paciente.nome.lower()
            self._indice_nome.setdefault(nome_key, []).append(paciente.id)
        return self.salvar_pacientes()

    def buscar_pacientes(self, **filtros) -> List[Paciente]:
        with self._lock:
            if len(filtros) == 1 and 'cpf' in filtros:
                cpf = filtros['cpf']
                if cpf in self._indice_cpf:
                    paciente = self.pacientes.get(self._indice_cpf[cpf])
                    if paciente and paciente.ativo:
                        return [paciente]
                return []

            resultados = []
            for paciente in self.pacientes.values():
                if not paciente.ativo:
                    continue
                match = True
                for campo, valor in filtros.items():
                    attr = getattr(paciente, campo, '')
                    if valor.lower() not in str(attr).lower():
                        match = False
                        break
                if match:
                    resultados.append(paciente)
            return resultados

    def obter_paciente(self, paciente_id: str) -> Optional[Paciente]:
        return self.pacientes.get(paciente_id)

    def atualizar_paciente(self, paciente_id: str, **atualizacoes) -> bool:
        with self._lock:
            if paciente_id not in self.pacientes:
                return False
            paciente = self.pacientes[paciente_id]
            
            # Atualizar índices de CPF
            if 'cpf' in atualizacoes and paciente.cpf != atualizacoes['cpf']:
                if paciente.cpf in self._indice_cpf:
                    del self._indice_cpf[paciente.cpf]
                if atualizacoes['cpf']:
                    self._indice_cpf[atualizacoes['cpf']] = paciente_id
            
            # Atualizar índice de nome se o nome mudar
            if 'nome' in atualizacoes and paciente.nome != atualizacoes['nome']:
                nome_antigo = paciente.nome.lower()
                if nome_antigo in self._indice_nome:
                    # Remove o ID da lista antiga
                    self._indice_nome[nome_antigo] = [pid for pid in self._indice_nome[nome_antigo] if pid != paciente_id]
                    if not self._indice_nome[nome_antigo]:
                        del self._indice_nome[nome_antigo]
                # Adiciona no novo nome
                nome_novo = atualizacoes['nome'].lower()
                self._indice_nome.setdefault(nome_novo, []).append(paciente_id)
            
            # Aplicar atualizações
            for campo, valor in atualizacoes.items():
                if hasattr(paciente, campo):
                    setattr(paciente, campo, valor)
            paciente.data_atualizacao = datetime.now().isoformat()
        return self.salvar_pacientes()

    def adicionar_diagnostico(self, diagnostico: Diagnostico) -> bool:
        return self.historico_manager.adicionar(diagnostico)

    def obter_historico_paciente(self, paciente_id: str) -> List[Diagnostico]:
        return self.historico_manager.obter_por_paciente(paciente_id)

    @property
    def historico(self) -> List[Diagnostico]:
        return self.historico_manager.obter_todos()

    def obter_doencas(self) -> List[Doenca]:
        return self.doencas

    def obter_sintomas_unicos(self) -> List[str]:
        sintomas = set()
        for d in self.doencas:
            for s in d.sintomas:
                nome = s["s"] if isinstance(s, dict) else str(s)
                sintomas.add(nome)
        return sorted(sintomas)

    def get_estatisticas(self) -> Dict:
        with self._lock:
            total = len(self.pacientes)
            ativos = sum(1 for p in self.pacientes.values() if p.ativo)
            homens = sum(1 for p in self.pacientes.values()
                        if p.ativo and p.sexo.lower() in ('m', 'masculino', 'homem'))
        
        stats_hist = self.historico_manager.get_estatisticas()
        
        return {
            'pacientes': {
                'total': total,
                'ativos': ativos,
                'inativos': total - ativos,
                'homens': homens,
                'mulheres': ativos - homens
            },
            'diagnosticos': {
                'total': stats_hist['total'],
                'ultimo_mes': int(stats_hist['media_diaria_ultimo_mes'] * 30)
            },
            'doencas': {
                'total': len(self.doencas),
                'fisicas': sum(1 for d in self.doencas if d.tipo == 'físico'),
                'psicologicas': sum(1 for d in self.doencas if d.tipo == 'psicológico')
            }
        }
    