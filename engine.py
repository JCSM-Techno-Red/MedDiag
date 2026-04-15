"""
Motor de diagnóstico otimizado
"""
from typing import List, Dict, Set
import hashlib

from config import CONFIG
from models import Doenca
from utils import setup_logging

logger = setup_logging()


class ResultadoDiagnostico:
    """Resultado de diagnóstico"""
    __slots__ = ('doenca', 'sintomas_selecionados', 'sintomas_correspondentes',
                 'sintomas_faltantes', 'pontuacao_bruta', 'pontuacao_maxima',
                 'porcentagem')

    def __init__(self, doenca: Doenca, sintomas_set: Set[str]):
        self.doenca = doenca
        self.sintomas_selecionados = sintomas_set
        self.sintomas_correspondentes = []
        self.sintomas_faltantes = []
        self.pontuacao_bruta = 0.0
        self.pontuacao_maxima = 0.0
        self.porcentagem = 0.0
        self._calcular()

    def _calcular(self):
        sintomas_doenca = {}
        for item in self.doenca.sintomas:
            if isinstance(item, dict):
                nome = item["s"]
                peso = float(item.get("peso", 1.0))
            else:
                nome = str(item)
                peso = 1.0
            sintomas_doenca[nome] = peso
            self.pontuacao_maxima += peso

        for nome, peso in sintomas_doenca.items():
            if nome in self.sintomas_selecionados:
                self.pontuacao_bruta += peso
                self.sintomas_correspondentes.append(nome)
            else:
                self.sintomas_faltantes.append(nome)

        if self.pontuacao_maxima > 0:
            self.porcentagem = round((self.pontuacao_bruta / self.pontuacao_maxima) * 100, 1)

    def to_dict(self) -> Dict:
        return {
            "doenca": self.doenca.nome,
            "tipo": self.doenca.tipo,
            "categoria": self.doenca.categoria,
            "descricao": self.doenca.descricao,
            "tratamento": self.doenca.tratamento,
            "severidade": self.doenca.severidade,
            "porcentagem": self.porcentagem,
            "sintomas_correspondentes": self.sintomas_correspondentes,
            "sintomas_faltantes": self.sintomas_faltantes,
            "pontuacao_bruta": round(self.pontuacao_bruta, 2),
            "pontuacao_maxima": round(self.pontuacao_maxima, 2)
        }


class DiagnosticoEngine:
    """Motor de diagnóstico com cache"""

    def __init__(self, database):
        self.db = database
        self.cache = {}
        self.cache_max_size = CONFIG.get("CACHE_MAX_SIZE", 1000)
        self._preprocessar_doencas()
        logger.info(f"Engine inicializado com {len(self.db.doencas)} doenças")

    def _preprocessar_doencas(self):
        for doenca in self.db.doencas:
            doenca._sintomas_nomes = set(
                item["s"] if isinstance(item, dict) else str(item)
                for item in doenca.sintomas
            )
            doenca._obrigatorios = set(doenca.condicoes.get("sintomas_obrigatorios", []))
            doenca._min_sintomas = doenca.condicoes.get("min_sintomas", 0)

    def avaliar(self, sintomas: List[str], paciente_id: str = None) -> List[Dict]:
        if not sintomas:
            return []

        sintomas_set = set(sintomas)
        cache_key = self._gerar_cache_key(sintomas)

        if cache_key in self.cache:
            return self.cache[cache_key]

        resultados = []
        porcentagem_minima = CONFIG["PORCENTAGEM_MINIMA"]
        limite_resultados = CONFIG["LIMITE_RESULTADOS"]

        for doenca in self.db.doencas:
            if not self._verificar_condicoes(doenca, sintomas_set):
                continue

            resultado = ResultadoDiagnostico(doenca, sintomas_set)
            if resultado.porcentagem >= porcentagem_minima:
                resultados.append(resultado.to_dict())

        resultados.sort(key=lambda x: x["porcentagem"], reverse=True)
        resultados = resultados[:limite_resultados]

        self._add_to_cache(cache_key, resultados)
        return resultados

    def _verificar_condicoes(self, doenca: Doenca, sintomas_set: Set[str]) -> bool:
        if doenca._obrigatorios and not doenca._obrigatorios.issubset(sintomas_set):
            return False
        if doenca._min_sintomas > 0:
            comuns = len(doenca._sintomas_nomes.intersection(sintomas_set))
            if comuns < doenca._min_sintomas:
                return False
        return True

    def _gerar_cache_key(self, sintomas: List[str]) -> str:
        return hashlib.md5(','.join(sorted(sintomas)).encode()).hexdigest()

    def _add_to_cache(self, key: str, value: List[Dict]):
        if len(self.cache) >= self.cache_max_size:
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = value

    def clear_cache(self):
        self.cache.clear()
        logger.info("Cache do engine limpo")