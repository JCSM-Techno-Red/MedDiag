"""
Interface gráfica principal - Sistema de Diagnóstico Médico
Versão simplificada sem painel de detalhes
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from typing import List, Optional, Dict
from datetime import datetime

from config import CONFIG
from models import Paciente, Diagnostico
from database import Database
from engine import DiagnosticoEngine
from utils import setup_logging, formatar_data, calcular_idade
from export import exportar_diagnostico, exportar_historico, exportar_paciente

logger = setup_logging()


class ModernStyle:
    """Configurações de estilo moderno para a interface"""
    
    PRIMARY = "#2563eb"
    PRIMARY_DARK = "#1d4ed8"
    PRIMARY_LIGHT = "#dbeafe"
    SECONDARY = "#10b981"
    SECONDARY_DARK = "#059669"
    SECONDARY_LIGHT = "#d1fae5"
    DANGER = "#ef4444"
    WARNING = "#f59e0b"
    WARNING_LIGHT = "#fef3c7"
    BG_MAIN = "#f8fafc"
    BG_CARD = "#ffffff"
    TEXT_PRIMARY = "#1e293b"
    TEXT_SECONDARY = "#64748b"
    TEXT_MUTED = "#94a3b8"
    BORDER = "#e2e8f0"

    @classmethod
    def configure_ttk_styles(cls):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('.', background=cls.BG_MAIN, foreground=cls.TEXT_PRIMARY,
                       fieldbackground=cls.BG_CARD, borderwidth=1, relief='flat')
        style.configure('TFrame', background=cls.BG_MAIN)
        style.configure('TLabelframe', background=cls.BG_MAIN, bordercolor=cls.BORDER)
        style.configure('TLabelframe.Label', background=cls.BG_MAIN,
                       foreground=cls.TEXT_PRIMARY, font=('Segoe UI', 10, 'bold'))
        style.configure('TLabel', background=cls.BG_MAIN,
                       foreground=cls.TEXT_PRIMARY, font=('Segoe UI', 9))
        style.configure('TButton', background=cls.BG_CARD, foreground=cls.TEXT_PRIMARY,
                       borderwidth=1, bordercolor=cls.BORDER, padding=(10, 5))
        style.map('TButton', background=[('active', cls.PRIMARY_LIGHT)])
        style.configure('Success.TButton', background=cls.SECONDARY, foreground='white',
                       borderwidth=0, font=('Segoe UI', 9, 'bold'), padding=(15, 8))
        style.map('Success.TButton', background=[('active', cls.SECONDARY_DARK)])
        style.configure('TEntry', fieldbackground=cls.BG_CARD, bordercolor=cls.BORDER, padding=8)
        style.configure('TCombobox', fieldbackground=cls.BG_CARD, bordercolor=cls.BORDER, padding=5)
        style.configure('Treeview', background=cls.BG_CARD, foreground=cls.TEXT_PRIMARY,
                       fieldbackground=cls.BG_CARD, rowheight=30, font=('Segoe UI', 9))
        style.configure('Treeview.Heading', background=cls.PRIMARY_LIGHT,
                       foreground=cls.TEXT_PRIMARY, font=('Segoe UI', 9, 'bold'))
        style.map('Treeview', background=[('selected', cls.PRIMARY)],
                  foreground=[('selected', 'white')])
        style.configure('TProgressbar', background=cls.PRIMARY, troughcolor=cls.BORDER)
        style.configure('TNotebook', background=cls.BG_MAIN, borderwidth=0)
        style.configure('TNotebook.Tab', background=cls.BG_CARD,
                       foreground=cls.TEXT_PRIMARY, padding=(15, 8))
        style.map('TNotebook.Tab', background=[('selected', cls.PRIMARY)],
                  foreground=[('selected', 'white')])


class PacienteDialog:
    """Diálogo de cadastro de pacientes com revisão e confirmação final"""

    def __init__(self, parent, paciente: Paciente = None, title="Cadastrar Paciente"):
        self.parent = parent
        self.paciente = paciente
        self.result = None
        self.entries = {}

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("850x750")
        self.dialog.minsize(700, 650)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.configure(bg=ModernStyle.BG_MAIN)

        # Centralizar
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 425
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 375
        self.dialog.geometry(f'+{x}+{y}')
        self.dialog.resizable(True, True)

        self._create_widgets()
        if paciente:
            self._preencher_dados()

        self.dialog.bind('<Return>', lambda e: self._avancar_ou_salvar())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())

    # -------------------------------------------------------------------------
    # Criação da interface com abas
    # -------------------------------------------------------------------------
    def _create_widgets(self):
        # Header
        header = tk.Frame(self.dialog, bg=ModernStyle.PRIMARY, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="👤 Cadastro de Paciente",
                font=('Segoe UI', 18, 'bold'),
                fg='white', bg=ModernStyle.PRIMARY).pack(pady=18)

        # Notebook (abas)
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Aba 1: Dados Pessoais
        self.tab_pessoal = tk.Frame(self.notebook, bg=ModernStyle.BG_MAIN)
        self.notebook.add(self.tab_pessoal, text="  📋 Dados Pessoais  ")
        self._create_tab_pessoal()

        # Aba 2: Contato e Endereço
        self.tab_contato = tk.Frame(self.notebook, bg=ModernStyle.BG_MAIN)
        self.notebook.add(self.tab_contato, text="  📞 Contato & Endereço  ")
        self._create_tab_contato()

        # Aba 3: Emergência e Observações
        self.tab_extra = tk.Frame(self.notebook, bg=ModernStyle.BG_MAIN)
        self.notebook.add(self.tab_extra, text="  🚨 Emergência & Obs  ")
        self._create_tab_extra()

        # Aba 4: Revisão e Confirmação
        self.tab_revisao = tk.Frame(self.notebook, bg=ModernStyle.BG_MAIN)
        self.notebook.add(self.tab_revisao, text="  ✅ Revisão  ")
        self._create_tab_revisao()

        # Footer com navegação
        footer = tk.Frame(self.dialog, bg=ModernStyle.BG_CARD, height=60)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        tk.Frame(self.dialog, bg=ModernStyle.BORDER, height=1).pack(fill=tk.X, side=tk.BOTTOM)

        footer_content = tk.Frame(footer, bg=ModernStyle.BG_CARD)
        footer_content.pack(fill=tk.X, padx=20, pady=12)

        self.status_label = tk.Label(footer_content, text="🟡 Preencha os dados do paciente",
                                     font=('Segoe UI', 9),
                                     fg=ModernStyle.TEXT_SECONDARY,
                                     bg=ModernStyle.BG_CARD)
        self.status_label.pack(side=tk.LEFT)

        # Botões de navegação
        btn_frame = tk.Frame(footer_content, bg=ModernStyle.BG_CARD)
        btn_frame.pack(side=tk.RIGHT)

        self.btn_anterior = ttk.Button(btn_frame, text="◀ Anterior", command=self._aba_anterior, width=12)
        self.btn_anterior.pack(side=tk.LEFT, padx=5)

        self.btn_proximo = ttk.Button(btn_frame, text="Próximo ▶", command=self._aba_proximo, width=12)
        self.btn_proximo.pack(side=tk.LEFT, padx=5)

        self.btn_salvar = ttk.Button(btn_frame, text="💾 Confirmar e Salvar",
                                     command=self._confirmar_e_salvar,
                                     style='Success.TButton', width=20)

        ttk.Button(btn_frame, text="❌ Cancelar", command=self.dialog.destroy, width=12).pack(side=tk.LEFT, padx=5)

        self._atualizar_botoes()

    def _atualizar_botoes(self):
        aba_atual = self.notebook.index(self.notebook.select())
        total_abas = self.notebook.index("end") - 1

        if aba_atual == 0:
            self.btn_anterior.pack_forget()
        else:
            self.btn_anterior.pack(side=tk.LEFT, padx=5)

        if aba_atual == total_abas:
            self.btn_proximo.pack_forget()
            self.btn_salvar.pack(side=tk.LEFT, padx=5)
        else:
            self.btn_proximo.pack(side=tk.LEFT, padx=5)
            self.btn_salvar.pack_forget()

        if aba_atual == total_abas:
            self.status_label.config(text="🔍 Revise os dados antes de salvar")
        else:
            self.status_label.config(text="🟡 Preencha os dados do paciente")

    def _aba_anterior(self):
        atual = self.notebook.index(self.notebook.select())
        if atual > 0:
            self.notebook.select(atual - 1)
            self._atualizar_botoes()

    def _aba_proximo(self):
        atual = self.notebook.index(self.notebook.select())
        total = self.notebook.index("end") - 1
        if atual < total:
            if atual + 1 == total:
                self._atualizar_resumo()
            self.notebook.select(atual + 1)
            self._atualizar_botoes()

    def _avancar_ou_salvar(self):
        atual = self.notebook.index(self.notebook.select())
        total = self.notebook.index("end") - 1
        if atual < total:
            self._aba_proximo()
        else:
            self._confirmar_e_salvar()

    # -------------------------------------------------------------------------
    # Criação das abas de formulário
    # -------------------------------------------------------------------------
    def _create_labeled_entry(self, parent, label, field, width=50, required=False):
        frame = tk.Frame(parent, bg=ModernStyle.BG_MAIN)
        frame.pack(fill=tk.X, pady=6)

        label_text = f"{label}{' *' if required else ''}"
        lbl = tk.Label(frame, text=label_text, font=('Segoe UI', 10),
                      fg=ModernStyle.DANGER if required else ModernStyle.TEXT_SECONDARY,
                      bg=ModernStyle.BG_MAIN, width=20, anchor=tk.W)
        lbl.pack(side=tk.LEFT, padx=(0, 10))

        if field == "sexo":
            var = tk.StringVar()
            widget = ttk.Combobox(frame, textvariable=var, width=width,
                                  values=["Masculino", "Feminino", "Outro"], state="readonly")
        elif field == "estado_civil":
            var = tk.StringVar()
            widget = ttk.Combobox(frame, textvariable=var, width=width,
                                  values=["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"],
                                  state="readonly")
        elif field == "tipo_sanguineo":
            var = tk.StringVar()
            widget = ttk.Combobox(frame, textvariable=var, width=width,
                                  values=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Desconhecido"],
                                  state="readonly")
        elif field == "estado":
            var = tk.StringVar()
            widget = ttk.Combobox(frame, textvariable=var, width=width,
                                  values=CONFIG["PACIENTE"]["estados"], state="readonly")
        elif field == "pais":
            var = tk.StringVar(value="Brasil")
            widget = ttk.Combobox(frame, textvariable=var, width=width,
                                  values=["Brasil", "Portugal", "Angola", "Moçambique", "Outro"], state="readonly")
        else:
            var = tk.StringVar()
            widget = ttk.Entry(frame, textvariable=var, width=width)
            if field == "data_nascimento":
                var.trace_add('write', lambda *args: self._calcular_idade())

        widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entries[field] = var
        return frame

    def _create_tab_pessoal(self):
        container = tk.Frame(self.tab_pessoal, bg=ModernStyle.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        canvas = tk.Canvas(container, bg=ModernStyle.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=ModernStyle.BG_MAIN)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=750)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(scroll_frame, text="📋 Dados Pessoais",
                font=('Segoe UI', 13, 'bold'),
                fg=ModernStyle.PRIMARY, bg=ModernStyle.BG_MAIN).pack(anchor=tk.W, pady=(0, 15))

        self._create_labeled_entry(scroll_frame, "Nome Completo", "nome", 60, True)
        self._create_labeled_entry(scroll_frame, "Data Nascimento (DD/MM/AAAA)", "data_nascimento", 25, True)
        self._create_labeled_entry(scroll_frame, "Sexo", "sexo", 25, True)
        self._create_labeled_entry(scroll_frame, "CPF", "cpf", 25)
        self._create_labeled_entry(scroll_frame, "RG", "rg", 25)
        self._create_labeled_entry(scroll_frame, "Estado Civil", "estado_civil", 25)
        self._create_labeled_entry(scroll_frame, "Tipo Sanguíneo", "tipo_sanguineo", 20)

        # Idade calculada
        idade_frame = tk.Frame(scroll_frame, bg=ModernStyle.BG_MAIN)
        idade_frame.pack(fill=tk.X, pady=6)
        tk.Label(idade_frame, text="Idade (calculada)", font=('Segoe UI', 10),
                fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.BG_MAIN, width=20, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        self.idade_entry = tk.Entry(idade_frame, font=('Segoe UI', 10),
                                   bg=ModernStyle.PRIMARY_LIGHT, fg=ModernStyle.TEXT_PRIMARY,
                                   relief='flat', state='readonly')
        self.idade_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entries["idade_calc"] = self.idade_entry

    def _create_tab_contato(self):
        container = tk.Frame(self.tab_contato, bg=ModernStyle.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        canvas = tk.Canvas(container, bg=ModernStyle.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=ModernStyle.BG_MAIN)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=750)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Contato
        tk.Label(scroll_frame, text="📞 Contato",
                font=('Segoe UI', 13, 'bold'),
                fg=ModernStyle.PRIMARY, bg=ModernStyle.BG_MAIN).pack(anchor=tk.W, pady=(0, 15))

        self._create_labeled_entry(scroll_frame, "Telefone Fixo", "telefone", 30)
        self._create_labeled_entry(scroll_frame, "Celular", "celular", 30, True)
        self._create_labeled_entry(scroll_frame, "Email", "email", 60)
        self._create_labeled_entry(scroll_frame, "WhatsApp", "whatsapp", 30)

        tk.Frame(scroll_frame, bg=ModernStyle.BORDER, height=2).pack(fill=tk.X, pady=20)

        # Endereço
        tk.Label(scroll_frame, text="🏠 Endereço",
                font=('Segoe UI', 13, 'bold'),
                fg=ModernStyle.PRIMARY, bg=ModernStyle.BG_MAIN).pack(anchor=tk.W, pady=(0, 15))

        self._create_labeled_entry(scroll_frame, "CEP", "cep", 20)
        self._create_labeled_entry(scroll_frame, "Logradouro", "endereco", 60)

        num_comp_frame = tk.Frame(scroll_frame, bg=ModernStyle.BG_MAIN)
        num_comp_frame.pack(fill=tk.X, pady=6)

        tk.Label(num_comp_frame, text="Número", font=('Segoe UI', 10),
                fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.BG_MAIN, width=20, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        var_num = tk.StringVar()
        ttk.Entry(num_comp_frame, textvariable=var_num, width=12).pack(side=tk.LEFT)
        self.entries["numero"] = var_num

        tk.Label(num_comp_frame, text="Complemento", font=('Segoe UI', 10),
                fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.BG_MAIN, width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(20, 10))
        var_comp = tk.StringVar()
        ttk.Entry(num_comp_frame, textvariable=var_comp, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entries["complemento"] = var_comp

        self._create_labeled_entry(scroll_frame, "Bairro", "bairro", 40)
        self._create_labeled_entry(scroll_frame, "Cidade", "cidade", 40)

                # País (apenas uma vez)
        est_pais_frame = tk.Frame(scroll_frame, bg=ModernStyle.BG_MAIN)
        est_pais_frame.pack(fill=tk.X, pady=6)

        tk.Label(est_pais_frame, text="Estado", font=('Segoe UI', 10),
                fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.BG_MAIN, width=20, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        var_est = tk.StringVar()
        ttk.Combobox(est_pais_frame, textvariable=var_est, values=CONFIG["PACIENTE"]["estados"],
                    width=10, state="readonly").pack(side=tk.LEFT)
        self.entries["estado"] = var_est

        tk.Label(est_pais_frame, text="País", font=('Segoe UI', 10),
                fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.BG_MAIN, width=8, anchor=tk.W).pack(side=tk.LEFT, padx=(20, 10))
        var_pais = tk.StringVar(value="Brasil")
        ttk.Combobox(est_pais_frame, textvariable=var_pais,
                    values=["Brasil", "Portugal", "Angola", "Moçambique", "Outro"],
                    width=18, state="readonly").pack(side=tk.LEFT)
        self.entries["pais"] = var_pais

    def _create_tab_extra(self):
        container = tk.Frame(self.tab_extra, bg=ModernStyle.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        canvas = tk.Canvas(container, bg=ModernStyle.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=ModernStyle.BG_MAIN)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=750)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Emergência
        tk.Label(scroll_frame, text="🚨 Contato de Emergência",
                font=('Segoe UI', 13, 'bold'),
                fg=ModernStyle.PRIMARY, bg=ModernStyle.BG_MAIN).pack(anchor=tk.W, pady=(0, 15))

        self._create_labeled_entry(scroll_frame, "Nome do Contato", "contato_emergencia_nome", 50)
        self._create_labeled_entry(scroll_frame, "Telefone", "contato_emergencia_telefone", 30)
        self._create_labeled_entry(scroll_frame, "Parentesco", "contato_emergencia_parentesco", 30)

        tk.Frame(scroll_frame, bg=ModernStyle.BORDER, height=2).pack(fill=tk.X, pady=20)

        # Observações
        tk.Label(scroll_frame, text="📝 Observações Gerais",
                font=('Segoe UI', 13, 'bold'),
                fg=ModernStyle.PRIMARY, bg=ModernStyle.BG_MAIN).pack(anchor=tk.W, pady=(0, 15))

        self.obs_text = scrolledtext.ScrolledText(scroll_frame, height=8, font=('Segoe UI', 10),
                                                  relief='solid', borderwidth=1)
        self.obs_text.pack(fill=tk.BOTH, expand=True)

    def _create_tab_revisao(self):
        container = tk.Frame(self.tab_revisao, bg=ModernStyle.BG_MAIN)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(container, text="🔍 Revise os dados do paciente",
                font=('Segoe UI', 13, 'bold'),
                fg=ModernStyle.PRIMARY, bg=ModernStyle.BG_MAIN).pack(anchor=tk.W, pady=(0, 15))

        text_frame = tk.Frame(container, bg=ModernStyle.BG_CARD, relief='solid', bd=1)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.resumo_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Consolas', 10),
                                                     bg=ModernStyle.BG_CARD, fg=ModernStyle.TEXT_PRIMARY,
                                                     relief='flat', borderwidth=0)
        self.resumo_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.resumo_text.configure(state="disabled")

        aviso = tk.Label(container, text="⚠️ Verifique se todos os dados estão corretos antes de salvar.",
                        font=('Segoe UI', 9, 'italic'),
                        fg=ModernStyle.WARNING, bg=ModernStyle.BG_MAIN)
        aviso.pack(pady=(10, 0))

    # -------------------------------------------------------------------------
    # Lógica de validação e resumo
    # -------------------------------------------------------------------------
    def _calcular_idade(self):
        data_nasc = self.entries.get("data_nascimento")
        if data_nasc:
            idade = calcular_idade(data_nasc.get())
            if idade > 0:
                self.idade_entry.config(state='normal')
                self.idade_entry.delete(0, tk.END)
                self.idade_entry.insert(0, str(idade))
                self.idade_entry.config(state='readonly')

    def _coletar_dados(self):
        dados = {}
        for field, var in self.entries.items():
            if field != "idade_calc":
                if hasattr(var, 'get'):
                    dados[field] = var.get().strip()
                else:
                    dados[field] = ""
        dados["observacoes"] = self.obs_text.get(1.0, tk.END).strip()
        return dados

    def _atualizar_resumo(self):
        dados = self._coletar_dados()
        linhas = []
        linhas.append("=" * 60)
        linhas.append("RESUMO DO CADASTRO".center(60))
        linhas.append("=" * 60)
        linhas.append("")
        linhas.append("📋 DADOS PESSOAIS")
        linhas.append("-" * 40)
        linhas.append(f"  Nome completo      : {dados.get('nome', '')}")
        linhas.append(f"  Data de nascimento : {dados.get('data_nascimento', '')}")
        linhas.append(f"  Sexo               : {dados.get('sexo', '')}")
        linhas.append(f"  CPF                : {dados.get('cpf', '')}")
        linhas.append(f"  RG                 : {dados.get('rg', '')}")
        linhas.append(f"  Estado civil       : {dados.get('estado_civil', '')}")
        linhas.append(f"  Tipo sanguíneo     : {dados.get('tipo_sanguineo', '')}")
        linhas.append("")
        linhas.append("📞 CONTATO")
        linhas.append("-" * 40)
        linhas.append(f"  Telefone fixo      : {dados.get('telefone', '')}")
        linhas.append(f"  Celular            : {dados.get('celular', '')}")
        linhas.append(f"  Email              : {dados.get('email', '')}")
        linhas.append(f"  WhatsApp           : {dados.get('whatsapp', '')}")
        linhas.append("")
        linhas.append("🏠 ENDEREÇO")
        linhas.append("-" * 40)
        linhas.append(f"  CEP                : {dados.get('cep', '')}")
        linhas.append(f"  Logradouro         : {dados.get('endereco', '')}")
        linhas.append(f"  Número             : {dados.get('numero', '')}")
        linhas.append(f"  Complemento        : {dados.get('complemento', '')}")
        linhas.append(f"  Bairro             : {dados.get('bairro', '')}")
        linhas.append(f"  Cidade             : {dados.get('cidade', '')}")
        linhas.append(f"  Estado             : {dados.get('estado', '')}")
        linhas.append(f"  País               : {dados.get('pais', 'Brasil')}")
        linhas.append("")
        linhas.append("🚨 CONTATO DE EMERGÊNCIA")
        linhas.append("-" * 40)
        linhas.append(f"  Nome               : {dados.get('contato_emergencia_nome', '')}")
        linhas.append(f"  Telefone           : {dados.get('contato_emergencia_telefone', '')}")
        linhas.append(f"  Parentesco         : {dados.get('contato_emergencia_parentesco', '')}")
        linhas.append("")
        linhas.append("📝 OBSERVAÇÕES")
        linhas.append("-" * 40)
        obs = dados.get('observacoes', '')
        if obs:
            for linha in obs.split('\n'):
                linhas.append(f"  {linha}")
        else:
            linhas.append("  (Nenhuma observação)")
        linhas.append("")
        linhas.append("=" * 60)

        texto_resumo = "\n".join(linhas)
        self.resumo_text.configure(state="normal")
        self.resumo_text.delete(1.0, tk.END)
        self.resumo_text.insert(1.0, texto_resumo)
        self.resumo_text.configure(state="disabled")

    def _validar_campos_obrigatorios(self):
        from utils import Validator
        obrigatorios = {
            "nome": "Nome Completo",
            "data_nascimento": "Data de Nascimento",
            "sexo": "Sexo",
            "celular": "Celular"
        }
        dados = self._coletar_dados()
        faltantes = []
        for field, nome in obrigatorios.items():
            if not dados.get(field):
                faltantes.append(nome)
        if faltantes:
            raise ValueError("Campos obrigatórios não preenchidos:\n• " + "\n• ".join(faltantes))
        
        # Validações opcionais
        if dados.get('cpf') and not Validator.validar_cpf(dados['cpf']):
            raise ValueError("CPF inválido. Digite um CPF válido (apenas números ou com pontos e traço).")
        if dados.get('email') and not Validator.validar_email(dados['email']):
            raise ValueError("E-mail inválido. Verifique o formato.")
        if dados.get('telefone') and not Validator.validar_telefone(dados['telefone']):
            raise ValueError("Telefone fixo inválido. Use DDD + número (8 ou 9 dígitos).")
        if dados.get('celular') and not Validator.validar_telefone(dados['celular']):
            raise ValueError("Celular inválido. Use DDD + 9 dígitos (ex: 11999999999).")

    def _confirmar_e_salvar(self):
        try:
            self._validar_campos_obrigatorios()
            dados = self._coletar_dados()
            resposta = messagebox.askyesno(
                "💾 Confirmar Cadastro",
                f"Deseja realmente salvar o paciente?\n\n"
                f"👤 {dados['nome']}\n"
                f"📅 {dados['data_nascimento']}\n"
                f"📱 {dados['celular']}\n\n"
                f"Após confirmar, os dados serão gravados.",
                icon='question'
            )
            if resposta:
                self.result = dados
                self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("❌ Erro de validação", str(e))
            self.notebook.select(0)

    def _limpar_campos(self):
        if messagebox.askyesno("🧹 Limpar Campos", "Deseja limpar todos os campos preenchidos?", icon='warning'):
            for var in self.entries.values():
                if hasattr(var, 'set'):
                    var.set("")
                elif isinstance(var, tk.Entry):
                    var.config(state='normal')
                    var.delete(0, tk.END)
                    var.config(state='readonly')
            self.obs_text.delete(1.0, tk.END)
            self.status_label.config(text="🟡 Campos limpos")
            self._atualizar_resumo()

    def _preencher_dados(self):
        if self.paciente:
            for field, var in self.entries.items():
                valor = getattr(self.paciente, field, "")
                if valor and hasattr(var, 'set'):
                    var.set(valor)
            self.obs_text.insert(1.0, self.paciente.observacoes or "")
            self.status_label.config(text="🟢 Dados do paciente carregados")
            self._calcular_idade()
            self._atualizar_resumo()

    def show(self) -> Optional[dict]:
        self.dialog.wait_window()
        return self.result


class App:
    """Aplicação principal do Sistema de Diagnóstico Médico"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema de Diagnóstico Médico")
        self.root.geometry(CONFIG["WINDOW_SIZE"])
        
        ModernStyle.configure_ttk_styles()
        self.root.configure(bg=ModernStyle.BG_MAIN)

        # Centralizar
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f'+{x}+{y}')

        self.db = Database()
        self.engine = DiagnosticoEngine(self.db)
        self.paciente_atual: Optional[Paciente] = None
        self.sintomas_selecionados = set()
        self.resultados_atuais = []
        self.sintomas_checkboxes = []

        self._verificar_dados()
        self._create_widgets()
        self._bind_shortcuts()

    def _verificar_dados(self):
        print(f"Pacientes: {len(self.db.pacientes)} | Doenças: {len(self.db.doencas)} | Histórico: {len(self.db.historico)}")
        if len(self.db.doencas) == 0:
            messagebox.showwarning("Aviso", "Nenhuma doença carregada. Verifique sintomas.json")

    def _create_widgets(self):
        self._create_menu()

        main = tk.Frame(self.root, bg=ModernStyle.BG_MAIN)
        main.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Header
        header = tk.Frame(main, bg=ModernStyle.BG_MAIN, height=50)
        header.pack(fill=tk.X, pady=(0, 15))
        header.pack_propagate(False)
        
        tk.Label(header, text="🏥 Sistema de Diagnóstico Médico",
                font=('Segoe UI', 18, 'bold'), fg=ModernStyle.PRIMARY, bg=ModernStyle.BG_MAIN).pack(side=tk.LEFT)
        tk.Label(header, text=datetime.now().strftime("%d/%m/%Y"),
                font=('Segoe UI', 10), fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.BG_MAIN).pack(side=tk.RIGHT)

        # Layout principal
        content = tk.Frame(main, bg=ModernStyle.BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(content, bg=ModernStyle.BG_MAIN)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        right = tk.Frame(content, bg=ModernStyle.BG_MAIN, width=500)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        right.pack_propagate(False)

        self._create_paciente_panel(left)
        self._create_sintomas_panel(left)
        self._create_resultados_panel(right)

        self.progress = ttk.Progressbar(main, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(10, 0))
        self.progress.pack_forget()

        self._create_status_bar()

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Arquivo", menu=file_menu)
        file_menu.add_command(label="Novo Diagnóstico", command=self._novo_diagnostico)
        file_menu.add_separator()
        file_menu.add_command(label="Exportar Resultados", command=self._exportar_resultados)
        file_menu.add_command(label="Exportar Histórico", command=self._exportar_historico)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.root.quit)

        pac_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Pacientes", menu=pac_menu)
        pac_menu.add_command(label="Cadastrar", command=self._cadastrar_paciente)
        pac_menu.add_command(label="Buscar", command=self._buscar_paciente)
        pac_menu.add_command(label="Listar", command=self._listar_pacientes)
        pac_menu.add_separator()
        pac_menu.add_command(label="Exportar Ficha", command=self._exportar_ficha)
        pac_menu.add_command(label="Editar Paciente", command=self._editar_paciente)

        diag_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Diagnóstico", menu=diag_menu)
        diag_menu.add_command(label="Executar", command=self._executar_diagnostico)
        diag_menu.add_command(label="Limpar Sintomas", command=self._limpar_sintomas)
        diag_menu.add_separator()
        diag_menu.add_command(label="Ver Histórico", command=self._ver_historico)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(label="Sobre", command=self._sobre)
        help_menu.add_command(label="Estatísticas", command=self._mostrar_estatisticas)

    def _editar_paciente(self):
        if not self.paciente_atual:
            messagebox.showwarning("Aviso", "Selecione um paciente primeiro.")
            return
        dialog = PacienteDialog(self.root, paciente=self.paciente_atual, title="Editar Paciente")
        dados = dialog.show()
        if dados:
            try:
                # Atualiza apenas os campos fornecidos
                self.db.atualizar_paciente(self.paciente_atual.id, **dados)
                # Recarrega o paciente atual
                self.paciente_atual = self.db.obter_paciente(self.paciente_atual.id)
                self.paciente_nome_var.set(self.paciente_atual.nome)
                self.paciente_id_var.set(f"ID: {self.paciente_atual.id[:8]}...")
                self._atualizar_status_stats()
                messagebox.showinfo("Sucesso", "Paciente atualizado com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", str(e))

    def _create_paciente_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" Paciente ", bg=ModernStyle.BG_MAIN,
                             fg=ModernStyle.TEXT_PRIMARY, font=('Segoe UI', 10, 'bold'))
        frame.pack(fill=tk.X, pady=(0, 15))

        content = tk.Frame(frame, bg=ModernStyle.BG_MAIN)
        content.pack(fill=tk.X, padx=15, pady=15)

        card = tk.Frame(content, bg=ModernStyle.PRIMARY_LIGHT)
        card.pack(fill=tk.X, pady=(0, 10))
        
        info = tk.Frame(card, bg=ModernStyle.PRIMARY_LIGHT)
        info.pack(fill=tk.X, padx=15, pady=10)

        self.paciente_nome_var = tk.StringVar(value="Nenhum paciente selecionado")
        tk.Label(info, text="👤", font=('Segoe UI', 24), bg=ModernStyle.PRIMARY_LIGHT).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(info, textvariable=self.paciente_nome_var, font=('Segoe UI', 12, 'bold'),
                fg=ModernStyle.PRIMARY_DARK, bg=ModernStyle.PRIMARY_LIGHT).pack(side=tk.LEFT)
        
        self.paciente_id_var = tk.StringVar()
        tk.Label(info, textvariable=self.paciente_id_var, font=('Segoe UI', 9),
                fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.PRIMARY_LIGHT).pack(side=tk.RIGHT)

        btn_frame = tk.Frame(content, bg=ModernStyle.BG_MAIN)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Selecionar", command=self._selecionar_paciente).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Cadastrar", command=self._cadastrar_paciente).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Ver Ficha", command=self._ver_ficha).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Limpar", command=self._limpar_paciente).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Executar Diagnóstico", style='Success.TButton',
                  command=self._executar_diagnostico).pack(side=tk.RIGHT, padx=2)

    def _create_sintomas_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" Sintomas ", bg=ModernStyle.BG_MAIN,
                             fg=ModernStyle.TEXT_PRIMARY, font=('Segoe UI', 10, 'bold'))
        frame.pack(fill=tk.BOTH, expand=True)

        content = tk.Frame(frame, bg=ModernStyle.BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        search = tk.Frame(content, bg=ModernStyle.BG_MAIN)
        search.pack(fill=tk.X, pady=(0, 15))

        tk.Label(search, text="🔎", font=('Segoe UI', 12), bg=ModernStyle.BG_MAIN).pack(side=tk.LEFT, padx=(0, 5))
        self.busca_var = tk.StringVar()
        self.busca_entry = ttk.Entry(search, textvariable=self.busca_var)
        self.busca_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.busca_entry.bind("<KeyRelease>", self._filtrar_sintomas)

        canvas_frame = tk.Frame(content, bg=ModernStyle.BG_MAIN)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg=ModernStyle.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        self.sintomas_container = tk.Frame(self.canvas, bg=ModernStyle.BG_CARD)

        self.sintomas_container.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.sintomas_container, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = tk.Frame(content, bg=ModernStyle.BG_MAIN)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(btn_frame, text="Selecionar Todos", command=self._selecionar_tudo_sintomas).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Limpar Todos", command=self._limpar_sintomas).pack(side=tk.LEFT, padx=2)
        
        self.label_contador = tk.Label(btn_frame, text="0 selecionados",
                                       font=('Segoe UI', 9, 'bold'), fg=ModernStyle.PRIMARY, bg=ModernStyle.BG_MAIN)
        self.label_contador.pack(side=tk.RIGHT)

        self._carregar_sintomas()

    def _create_resultados_panel(self, parent):
        frame = tk.LabelFrame(parent, text=" Resultados do Diagnóstico ", bg=ModernStyle.BG_MAIN,
                             fg=ModernStyle.TEXT_PRIMARY, font=('Segoe UI', 10, 'bold'))
        frame.pack(fill=tk.BOTH, expand=True)

        content = tk.Frame(frame, bg=ModernStyle.BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        columns = ("Doença", "Compatibilidade", "Severidade", "Tipo")
        self.tree = ttk.Treeview(content, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
        self.tree.column("Doença", width=220)
        self.tree.column("Compatibilidade", width=100)
        self.tree.column("Severidade", width=90)
        self.tree.column("Tipo", width=80)

        scroll = ttk.Scrollbar(content, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.label_sem_resultados = tk.Label(content, text="Execute um diagnóstico para ver os resultados",
                                            font=('Segoe UI', 10, 'italic'),
                                            fg=ModernStyle.TEXT_MUTED, bg=ModernStyle.BG_MAIN)
        self.label_sem_resultados.place(relx=0.5, rely=0.5, anchor="center")

    def _create_status_bar(self):
        self.status_frame = tk.Frame(self.root, bg=ModernStyle.PRIMARY_LIGHT, height=25)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(self.status_frame, text="🟢 Pronto",
                                     font=('Segoe UI', 8), fg=ModernStyle.PRIMARY_DARK, bg=ModernStyle.PRIMARY_LIGHT)
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.status_stats = tk.Label(self.status_frame, text="", font=('Segoe UI', 8),
                                     fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.PRIMARY_LIGHT)
        self.status_stats.pack(side=tk.RIGHT, padx=10)
        self._atualizar_status_stats()

    def _atualizar_status_stats(self):
        stats = self.db.get_estatisticas()
        self.status_stats.config(text=f"{stats['pacientes']['ativos']} pacientes | {stats['doencas']['total']} doenças | {stats['diagnosticos']['total']} diagnósticos")

    def _bind_shortcuts(self):
        self.root.bind('<Control-n>', lambda e: self._novo_diagnostico())
        self.root.bind('<Control-d>', lambda e: self._executar_diagnostico())
        self.root.bind('<F5>', lambda e: self._executar_diagnostico())
        self.root.bind('<Control-f>', lambda e: self.busca_entry.focus())

    # ========== SINTOMAS ==========
    def _carregar_sintomas(self):
        self.sintomas_checkboxes.clear()
        for sintoma in self.db.obter_sintomas_unicos():
            var = tk.BooleanVar()
            frame = tk.Frame(self.sintomas_container, bg=ModernStyle.BG_CARD)
            frame.pack(fill=tk.X, padx=5, pady=1)
            
            cb = tk.Checkbutton(frame, text=sintoma.capitalize(), variable=var,
                              font=('Segoe UI', 9), bg=ModernStyle.BG_CARD,
                              activebackground=ModernStyle.PRIMARY_LIGHT,
                              command=lambda s=sintoma, v=var: self._toggle_sintoma(s, v))
            cb.pack(anchor=tk.W)
            self.sintomas_checkboxes.append((sintoma.lower(), var, frame))

    def _filtrar_sintomas(self, event=None):
        filtro = self.busca_var.get().lower()
        for sintoma, var, frame in self.sintomas_checkboxes:
            if filtro in sintoma:
                frame.pack(fill=tk.X, padx=5, pady=1)
            else:
                frame.pack_forget()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _toggle_sintoma(self, sintoma: str, var: tk.BooleanVar):
        if var.get():
            self.sintomas_selecionados.add(sintoma.lower())
        else:
            self.sintomas_selecionados.discard(sintoma.lower())
        self.label_contador.config(text=f"{len(self.sintomas_selecionados)} selecionados")

    def _selecionar_tudo_sintomas(self):
        for sintoma, var, frame in self.sintomas_checkboxes:
            if frame.winfo_ismapped():
                var.set(True)
                self.sintomas_selecionados.add(sintoma)
        self.label_contador.config(text=f"{len(self.sintomas_selecionados)} selecionados")

    def _limpar_sintomas(self):
        self.sintomas_selecionados.clear()
        for _, var, _ in self.sintomas_checkboxes:
            var.set(False)
        self.label_contador.config(text="0 selecionados")
        self._limpar_resultados()

    # ========== RESULTADOS ==========
    def _limpar_resultados(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.resultados_atuais = []
        self.label_sem_resultados.lift()

    # ========== PACIENTES ==========
    def _selecionar_paciente(self):
        pacientes = [p for p in self.db.pacientes.values() if p.ativo]
        if not pacientes:
            messagebox.showinfo("ℹ️ Informação", "Nenhum paciente cadastrado.")
            self._cadastrar_paciente()
            return

        win = tk.Toplevel(self.root)
        win.title("🔍 Selecionar Paciente")
        win.geometry("700x500")
        win.configure(bg=ModernStyle.BG_MAIN)
        win.transient(self.root)
        win.grab_set()

        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 350
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 250
        win.geometry(f'+{x}+{y}')

        header = tk.Frame(win, bg=ModernStyle.PRIMARY, height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="🔍 Selecione um Paciente",
                font=('Segoe UI', 16, 'bold'),
                fg='white', bg=ModernStyle.PRIMARY).pack(pady=18)

        main = tk.Frame(win, bg=ModernStyle.BG_MAIN)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(main, text="📋 Pacientes cadastrados (clique para selecionar):",
                font=('Segoe UI', 10),
                fg=ModernStyle.TEXT_SECONDARY, bg=ModernStyle.BG_MAIN).pack(anchor=tk.W, pady=(0, 10))

        tree_frame = tk.Frame(main, bg=ModernStyle.BG_MAIN)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Nome", "CPF", "Celular", "Idade")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        tree.heading("Nome", text="👤 Nome")
        tree.heading("CPF", text="🆔 CPF")
        tree.heading("Celular", text="📱 Celular")
        tree.heading("Idade", text="🎂 Idade")
        tree.column("Nome", width=250)
        tree.column("CPF", width=140)
        tree.column("Celular", width=130)
        tree.column("Idade", width=60)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for p in pacientes:
            idade = calcular_idade(p.data_nascimento) if p.data_nascimento else "N/A"
            tree.insert("", "end", values=(
                p.nome, p.cpf or "—", p.celular or p.telefone or "—", idade
            ), tags=(p.id,))

        tree.tag_configure('selected', background=ModernStyle.PRIMARY_LIGHT)

        paciente_selecionado_id = None
        paciente_selecionado_nome = None

        lbl_selecionado = tk.Label(main, text="Nenhum paciente selecionado",
                                   font=('Segoe UI', 9, 'italic'),
                                   fg=ModernStyle.TEXT_MUTED, bg=ModernStyle.BG_MAIN)
        lbl_selecionado.pack(anchor=tk.W, pady=(10, 0))

        btn_frame = tk.Frame(main, bg=ModernStyle.BG_MAIN)
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        btn_confirmar = ttk.Button(btn_frame, text="✓ Confirmar Seleção",
                                   style='Success.TButton', state='disabled')
        btn_confirmar.pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="✗ Cancelar", command=win.destroy).pack(side=tk.RIGHT, padx=5)

        def atualizar_label():
            if paciente_selecionado_nome:
                lbl_selecionado.config(text=f"✅ Selecionado: {paciente_selecionado_nome}", fg=ModernStyle.PRIMARY)
            else:
                lbl_selecionado.config(text="Nenhum paciente selecionado", fg=ModernStyle.TEXT_MUTED)

        def on_select(event=None):
            nonlocal paciente_selecionado_id, paciente_selecionado_nome
            selection = tree.selection()
            if selection:
                item = tree.item(selection[0])
                paciente_selecionado_id = item["tags"][0]
                paciente_selecionado_nome = item["values"][0]
                for sel in tree.selection():
                    tree.item(sel, tags=())
                tree.item(selection[0], tags=('selected',))
                btn_confirmar.config(state='normal')
            else:
                paciente_selecionado_id = None
                paciente_selecionado_nome = None
                btn_confirmar.config(state='disabled')
            atualizar_label()

        tree.bind('<<TreeviewSelect>>', on_select)
        tree.bind('<Double-1>', lambda e: confirmar_selecao())

        def confirmar_selecao():
            nonlocal paciente_selecionado_id
            if paciente_selecionado_id:
                paciente = self.db.obter_paciente(paciente_selecionado_id)
                if paciente:
                    self.paciente_atual = paciente
                    self.paciente_nome_var.set(paciente.nome)
                    self.paciente_id_var.set(f"ID: {paciente.id[:8]}...")
                    win.destroy()
                    messagebox.showinfo("✅ Paciente Selecionado", f"Paciente **{paciente.nome}** selecionado!")
                    self.status_label.config(text=f"🟢 Paciente: {paciente.nome}")
            else:
                messagebox.showwarning("⚠️ Aviso", "Selecione um paciente da lista.")

        btn_confirmar.config(command=confirmar_selecao)
        tree.focus_set()

    def _cadastrar_paciente(self):
        dialog = PacienteDialog(self.root)
        dados = dialog.show()
        if dados:
            try:
                paciente = Paciente.criar_novo(**dados)
                self.db.adicionar_paciente(paciente)
                self.paciente_atual = paciente
                self.paciente_nome_var.set(paciente.nome)
                self.paciente_id_var.set(f"ID: {paciente.id[:8]}...")
                self._atualizar_status_stats()
                messagebox.showinfo("Sucesso", "Paciente cadastrado!")
            except Exception as e:
                messagebox.showerror("Erro", str(e))

    def _buscar_paciente(self):
        termo = simpledialog.askstring("Buscar", "Nome ou CPF:", parent=self.root)
        if termo:
            pacientes = self.db.buscar_pacientes(nome=termo) or self.db.buscar_pacientes(cpf=termo)
            if pacientes:
                p = pacientes[0]
                self.paciente_atual = p
                self.paciente_nome_var.set(p.nome)
                self.paciente_id_var.set(f"ID: {p.id[:8]}...")
                messagebox.showinfo("Encontrado", f"Paciente: {p.nome}")
            else:
                messagebox.showinfo("Não encontrado", "Nenhum paciente encontrado.")

    def _listar_pacientes(self):
        pacientes = list(self.db.pacientes.values())
        if not pacientes:
            messagebox.showinfo("Pacientes", "Nenhum paciente cadastrado.")
            return

        win = tk.Toplevel(self.root)
        win.title("Pacientes")
        win.geometry("700x500")
        text = scrolledtext.ScrolledText(win, font=('Consolas', 9))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        txt = f"{'='*60}\nPACIENTES CADASTRADOS ({len(pacientes)})\n{'='*60}\n\n"
        for i, p in enumerate(pacientes, 1):
            txt += f"{i}. {p.nome}\n   CPF: {p.cpf or 'N/A'} | Cel: {p.celular or 'N/A'}\n"
            txt += f"   Status: {'Ativo' if p.ativo else 'Inativo'}\n{'-'*50}\n"
        text.insert(1.0, txt)
        text.configure(state="disabled")

    def _ver_ficha(self):
        if not self.paciente_atual:
            messagebox.showwarning("Aviso", "Selecione um paciente.")
            return
        win = tk.Toplevel(self.root)
        win.title(f"Ficha - {self.paciente_atual.nome}")
        win.geometry("500x400")
        text = scrolledtext.ScrolledText(win, font=('Consolas', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        p = self.paciente_atual
        txt = f"""
{'='*50}
FICHA DO PACIENTE
{'='*50}
Nome: {p.nome}
CPF: {p.cpf or 'N/A'}   RG: {p.rg or 'N/A'}
Nascimento: {p.data_nascimento or 'N/A'}
Sexo: {p.sexo or 'N/A'}   Estado Civil: {p.estado_civil or 'N/A'}
Tipo Sanguíneo: {p.tipo_sanguineo or 'N/A'}
CONTATO:
Telefone: {p.telefone or 'N/A'}   Celular: {p.celular or 'N/A'}
Email: {p.email or 'N/A'}
ENDEREÇO:
{p.endereco or 'N/A'}, {p.numero or 'S/N'} - {p.cidade or 'N/A'}/{p.estado or 'N/A'}
EMERGÊNCIA: {p.contato_emergencia_nome or 'N/A'} - {p.contato_emergencia_telefone or 'N/A'}
Status: {'Ativo' if p.ativo else 'Inativo'}
{'='*50}
"""
        text.insert(1.0, txt)
        text.configure(state="disabled")

    def _limpar_paciente(self):
        self.paciente_atual = None
        self.paciente_nome_var.set("Nenhum paciente selecionado")
        self.paciente_id_var.set("")

    # ========== DIAGNÓSTICO ==========
    def _executar_diagnostico(self):
        if not self.sintomas_selecionados:
            messagebox.showwarning("Aviso", "Selecione pelo menos um sintoma.")
            return

        self.progress.pack(fill=tk.X, pady=(10, 0))
        self.progress.start(10)
        self.status_label.config(text="Executando diagnóstico...")
        self.root.update_idletasks()

        try:
            resultados = self.engine.avaliar(list(self.sintomas_selecionados))
            self.resultados_atuais = resultados
            self._atualizar_resultados(resultados)

            if self.paciente_atual:
                diag = Diagnostico.criar_novo(self.paciente_atual, list(self.sintomas_selecionados), resultados)
                self.db.adicionar_diagnostico(diag)
                self._atualizar_status_stats()

            self.status_label.config(text=f"Diagnóstico concluído - {len(resultados)} resultados")
            messagebox.showinfo("Sucesso", f"{len(resultados)} resultados encontrados")
        except Exception as e:
            self.status_label.config(text="Erro")
            messagebox.showerror("Erro", str(e))
        finally:
            self.progress.stop()
            self.progress.pack_forget()

    def _atualizar_resultados(self, resultados):
        self._limpar_resultados()
        self.label_sem_resultados.lower()
        for r in resultados:
            self.tree.insert("", "end", values=(
                r["doenca"], f"{r['porcentagem']:.1f}%",
                r["severidade"].capitalize(), r["tipo"].capitalize()
            ))

    # ========== HISTÓRICO ==========
    def _ver_historico(self):
        if not self.db.historico:
            messagebox.showinfo("Histórico", "Nenhum diagnóstico registrado.")
            return

        win = tk.Toplevel(self.root)
        win.title("Histórico")
        win.geometry("900x500")
        tree = ttk.Treeview(win, columns=("Data", "Paciente", "Diagnóstico", "%"), show="headings")
        tree.heading("Data", text="Data")
        tree.heading("Paciente", text="Paciente")
        tree.heading("Diagnóstico", text="Diagnóstico")
        tree.heading("%", text="%")
        tree.column("Data", width=150)
        tree.column("Paciente", width=200)
        tree.column("Diagnóstico", width=350)
        tree.column("%", width=80)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for d in self.db.historico[:100]:
            tree.insert("", "end", values=(formatar_data(d.data_hora), d.paciente_nome,
                                           d.top_resultado, f"{d.top_porcentagem:.1f}%"))

    # ========== EXPORTAÇÃO ==========
    def _exportar_resultados(self):
        if not self.resultados_atuais:
            messagebox.showwarning("Aviso", "Nenhum resultado.")
            return
        p = self.paciente_atual.nome if self.paciente_atual else "Paciente"
        if exportar_diagnostico(p, list(self.sintomas_selecionados), self.resultados_atuais):
            messagebox.showinfo("Sucesso", "Exportado!")

    def _exportar_historico(self):
        if self.db.historico and exportar_historico(self.db.historico):
            messagebox.showinfo("Sucesso", "Exportado!")

    def _exportar_ficha(self):
        if self.paciente_atual and exportar_paciente(self.paciente_atual):
            messagebox.showinfo("Sucesso", "Exportado!")

    # ========== OUTROS ==========
    def _novo_diagnostico(self):
        self._limpar_sintomas()
        self._limpar_resultados()
        self.status_label.config(text="🟢 Pronto")

    def _mostrar_estatisticas(self):
        s = self.db.get_estatisticas()
        msg = f"""
ESTATÍSTICAS
Pacientes: {s['pacientes']['total']} ({s['pacientes']['ativos']} ativos)
Diagnósticos: {s['diagnosticos']['total']}
Doenças: {s['doencas']['total']} (Físicas: {s['doencas']['fisicas']}, Psicológicas: {s['doencas']['psicologicas']})
Sintomas: {len(self.db.obter_sintomas_unicos())}
"""
        messagebox.showinfo("Estatísticas", msg)

    def _sobre(self):
        s = self.db.get_estatisticas()
        msg = f"""
SISTEMA DE DIAGNÓSTICO MÉDICO v2.0
Pacientes: {s['pacientes']['total']}
Doenças: {s['doencas']['total']}
Diagnósticos: {s['diagnosticos']['total']}
Ferramenta de auxílio diagnóstico.
Não substitui consulta médica.
"""
        messagebox.showinfo("Sobre", msg)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()