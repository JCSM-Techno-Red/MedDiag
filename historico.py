"""
Gerenciamento de histórico de diagnósticos
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from config import CONFIG, ConfigManager
from models import Diagnostico
from utils import setup_logging, BackupManager, formatar_data

logger = setup_logging(CONFIG["LOG_FILE"])


class HistoricoManager:
    """Gerenciador do histórico de diagnósticos"""

    def __init__(self):
        self.historico_file = ConfigManager.get_path(CONFIG["HIST_FILE"])
        self.backup_manager = BackupManager(
            ConfigManager.get_path("backups"),
            CONFIG["BACKUP_DAYS_TO_KEEP"]
        )
        self.historico: List[Diagnostico] = []
        self._carregar()

    def _carregar(self) -> None:
        try:
            if not os.path.exists(self.historico_file):
                self.historico = []
                logger.info("Arquivo de histórico não encontrado. Iniciando vazio.")
                return

            with open(self.historico_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.historico = []
            erros = 0
            for item in data:
                try:
                    diagnostico = Diagnostico(
                        id=item.get('id', ''),
                        paciente_id=item.get('paciente_id', ''),
                        paciente_nome=item.get('paciente_nome', ''),
                        sintomas=item.get('sintomas', []),
                        data_hora=item.get('data_hora', ''),
                        resultados=item.get('resultados', []),
                        top_resultado=item.get('top_resultado', ''),
                        top_porcentagem=item.get('top_porcentagem', 0.0)
                    )
                    self.historico.append(diagnostico)
                except Exception as e:
                    logger.error(f"Erro ao carregar diagnóstico: {e}")
                    erros += 1
            
            self._ordenar()
            logger.info(f"Histórico carregado: {len(self.historico)} registros ({erros} erros)")
        except Exception as e:
            logger.error(f"Erro ao carregar histórico: {e}")
            self.historico = []

    def _salvar(self) -> bool:
        try:
            self.backup_manager.create_backup(self.historico_file, "historico")
            data = [{
                'id': d.id,
                'paciente_id': d.paciente_id,
                'paciente_nome': d.paciente_nome,
                'sintomas': d.sintomas,
                'data_hora': d.data_hora,
                'resultados': d.resultados,
                'top_resultado': d.top_resultado,
                'top_porcentagem': d.top_porcentagem
            } for d in self.historico]
            
            with open(self.historico_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Histórico salvo: {len(self.historico)} registros")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar histórico: {e}")
            return False

    def _ordenar(self) -> None:
        try:
            self.historico.sort(key=lambda x: x.data_hora if x.data_hora else "", reverse=True)
        except Exception:
            pass

    def adicionar(self, diagnostico: Diagnostico) -> bool:
        try:
            self.historico.insert(0, diagnostico)
            max_itens = CONFIG.get("MAX_HIST_ITENS", 500)
            if len(self.historico) > max_itens:
                self.historico = self.historico[:max_itens]
            return self._salvar()
        except Exception as e:
            logger.error(f"Erro ao adicionar diagnóstico: {e}")
            return False

    def obter_todos(self, limite: Optional[int] = None) -> List[Diagnostico]:
        if limite:
            return self.historico[:limite]
        return self.historico.copy()

    def obter_por_paciente(self, paciente_id: str) -> List[Diagnostico]:
        return [d for d in self.historico if d.paciente_id == paciente_id]

    def _parse_data(self, data_str: str) -> Optional[datetime]:
        try:
            if "T" in data_str:
                return datetime.fromisoformat(data_str.replace('Z', '+00:00'))
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(data_str, fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def get_estatisticas(self) -> Dict[str, Any]:
        total = len(self.historico)
        if total == 0:
            return {
                'total': 0,
                'pacientes_unicos': 0,
                'diagnosticos_mais_comuns': [],
                'ultimo_diagnostico': None,
                'media_diaria_ultimo_mes': 0
            }
        
        pacientes_unicos = len(set(d.paciente_id for d in self.historico))
        
        contagem = {}
        for d in self.historico:
            if d.top_resultado:
                contagem[d.top_resultado] = contagem.get(d.top_resultado, 0) + 1
        top_doencas = sorted(contagem.items(), key=lambda x: x[1], reverse=True)[:5]
        
        ultimo = self.historico[0]
        um_mes_atras = datetime.now() - timedelta(days=30)
        diags_mes = [d for d in self.historico
                     if (dt := self._parse_data(d.data_hora)) and dt >= um_mes_atras]
        media_diaria = len(diags_mes) / 30.0
        
        return {
            'total': total,
            'pacientes_unicos': pacientes_unicos,
            'diagnosticos_mais_comuns': top_doencas,
            'ultimo_diagnostico': {
                'data': formatar_data(ultimo.data_hora) if ultimo else None,
                'paciente': ultimo.paciente_nome if ultimo else None,
                'resultado': ultimo.top_resultado if ultimo else None
            },
            'media_diaria_ultimo_mes': round(media_diaria, 2)
        }

    def recarregar(self) -> None:
        self._carregar()