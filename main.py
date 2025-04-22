import tkinter as tk
from tkinter import messagebox
import customtkinter
import textwrap
import datetime
import sqlite3
import os

# --- PARTE 0: Gerenciador do Banco de Dados ---

class DatabaseManager:
    """Gerencia a conexão e as operações com o banco de dados SQLite."""
    def __init__(self, db_name="banco_moderno_v6_ptbr.db"): # Novo nome
        self.db_name = db_name
        self.initialize_db() # Cria tabelas se não existirem

    def _connect(self):
        """Estabelece a conexão com o banco de dados."""
        try:
            conn = sqlite3.connect(self.db_name)
            conn.execute("PRAGMA foreign_keys = ON;") # Habilita chaves estrangeiras
            conn.row_factory = sqlite3.Row # Retorna resultados como dicionários
            return conn
        except sqlite3.Error as e:
            print(f"Erro ao conectar ao BD: {e}")
            messagebox.showerror("Erro Crítico de BD", f"Não foi possível conectar ao banco de dados:\n{e}")
            raise # Re-levanta a exceção para interromper

    def execute_query(self, query, params=(), *, is_script=False):
        """Executa uma query que não retorna dados (INSERT, UPDATE, DELETE) ou um script."""
        conn = None
        try:
            conn = self._connect(); cursor = conn.cursor()
            if is_script: cursor.executescript(query) # Executa script SQL (várias instruções)
            else: cursor.execute(query, params) # Executa consulta única
            conn.commit(); return cursor.lastrowid # Confirma e retorna ID da última linha inserida
        except sqlite3.Error as e:
            print(f"Erro BD [Execute]: {e}\nQuery: {query}\nParams: {params}")
            if conn: conn.rollback() # Desfaz em caso de erro
            if "UNIQUE constraint failed" in str(e): print("Erro de constraint UNIQUE (valor duplicado).")
            # Não mostra messagebox para todos os erros para não poluir
            return None # Indica falha
        finally:
            if conn: conn.close() # Garante que a conexão seja fechada

    def fetch_one(self, query, params=()):
        """Executa uma query e retorna um único resultado (ou None)."""
        conn = None
        try:
            conn = self._connect(); cursor = conn.cursor()
            cursor.execute(query, params); return cursor.fetchone() # Busca um resultado
        except sqlite3.Error as e:
            print(f"Erro BD [Fetch One]: {e}\nQuery: {query}\nParams: {params}"); return None
        finally:
            if conn: conn.close()

    def fetch_all(self, query, params=()):
        """Executa uma query e retorna todos os resultados (ou lista vazia)."""
        conn = None
        try:
            conn = self._connect(); cursor = conn.cursor()
            cursor.execute(query, params); return cursor.fetchall() # Busca todos os resultados
        except sqlite3.Error as e:
            print(f"Erro BD [Fetch All]: {e}\nQuery: {query}\nParams: {params}"); return []
        finally:
            if conn: conn.close()

    def initialize_db(self):
        """Cria/Atualiza as tabelas do banco de dados se não existirem."""
        needs_setup = not os.path.exists(self.db_name) # Verifica se o arquivo BD já existe
        # Cria/Atualiza Tabela Clientes (com senha e role)
        try:
            conn = self._connect(); cursor = conn.cursor()
            # Cria tabela base se não existir
            cursor.execute("CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, cpf TEXT NOT NULL UNIQUE, endereco TEXT);")
            # Tenta adicionar colunas (ignora erro se já existirem)
            try: cursor.execute("ALTER TABLE clientes ADD COLUMN senha TEXT NOT NULL DEFAULT 'senha_padrao';"); print("Coluna 'senha' adicionada/verificada.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e): raise
            try: cursor.execute("ALTER TABLE clientes ADD COLUMN role TEXT NOT NULL DEFAULT 'user';"); print("Coluna 'role' adicionada/verificada.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e): raise
            conn.commit()
        except sqlite3.Error as e: print(f"Erro ao inicializar tabela clientes: {e}")
        finally:
             if conn: conn.close()
        # Cria Outras Tabelas (contas, transacoes)
        create_other_tables_script = """
        CREATE TABLE IF NOT EXISTS contas (id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT NOT NULL UNIQUE, agencia TEXT NOT NULL DEFAULT '0001', saldo REAL NOT NULL DEFAULT 0.0, limite REAL DEFAULT 500.0, limite_saques INTEGER DEFAULT 3, tipo_conta TEXT NOT NULL DEFAULT 'corrente', cliente_id INTEGER NOT NULL, FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS transacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, conta_id INTEGER NOT NULL, tipo TEXT NOT NULL CHECK(tipo IN ('deposito', 'saque', 'transferencia_enviada', 'transferencia_recebida')), valor REAL NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, conta_destino_id INTEGER DEFAULT NULL, FOREIGN KEY (conta_id) REFERENCES contas (id) ON DELETE CASCADE, FOREIGN KEY (conta_destino_id) REFERENCES contas(id));
        """
        print("Inicializando BD (contas, transacoes)...")
        self.execute_query(create_other_tables_script, is_script=True)
        print("Tabelas verificadas/criadas.")
        # Adiciona Admin se for a primeira execução
        if needs_setup:
            print("Primeira execução: Adicionando usuário ADMIN de exemplo...")
            try:
                admin_cpf = "000.000.000-00"; admin_senha_plana = "admin123" # SENHA INSEGURA!
                if not self.fetch_one("SELECT id FROM clientes WHERE cpf = ?", (admin_cpf,)):
                    admin_id = self.execute_query("INSERT INTO clientes (nome, cpf, endereco, senha, role) VALUES (?, ?, ?, ?, ?)", ("Admin Master", admin_cpf, "Sistema", admin_senha_plana, "admin"))
                    if admin_id:
                        self.execute_query("INSERT INTO contas (numero, cliente_id, saldo) VALUES (?, ?, ?)", ("9999", admin_id, 9999.0))
                        print(f"Usuário ADMIN (CPF: {admin_cpf}, Senha: {admin_senha_plana}) criado.")
                        messagebox.showinfo("Admin Criado", f"Admin criado:\nCPF: {admin_cpf}\nSenha: {admin_senha_plana}\nUse para o primeiro login.")
                    else: print("Erro ao inserir ADMIN.")
                else: print("ADMIN já existe.")
            except Exception as e: print(f"Erro dados de exemplo: {e}")

# --- PARTE 1: Classes do Modelo (comentários traduzidos) ---

class Cliente:
    """Representa um cliente do banco, interagindo com o BD (com senha e papel)."""
    def __init__(self, db_manager: DatabaseManager, cliente_id=None, nome=None, cpf=None, endereco=None, senha=None, role=None):
        self.db=db_manager; self.id=cliente_id; self.nome=nome; self.cpf=cpf; self.endereco=endereco;
        # **AVISO:** Armazenando senha em texto plano!
        self._senha_plana=senha; self.role=role if role else 'user' # Papel padrão 'user'
        if cliente_id is not None and not (nome or cpf): self._load_from_db() # Carrega se ID foi passado

    def _load_from_db(self):
        """Carrega os dados do cliente do BD usando o ID."""
        if self.id is None: return
        data = self.db.fetch_one("SELECT nome, cpf, endereco, senha, role FROM clientes WHERE id = ?", (self.id,))
        if data: self.nome, self.cpf, self.endereco, self._senha_plana, self.role = data['nome'], data['cpf'], data['endereco'], data['senha'], data['role']
        else: print(f"Erro: Cliente ID {self.id} não encontrado."); self.id=self.nome=self.cpf=self.endereco=self._senha_plana=self.role=None # Invalida objeto

    def save(self) -> bool:
        """Salva (INSERT ou UPDATE) os dados do cliente no BD."""
        if not self.nome or not self.cpf or not self._senha_plana: print("Erro: Nome, CPF, Senha obrigatórios."); return False
        # **AVISO:** Salvando senha em texto plano!
        if self.id is not None: # UPDATE
            q="UPDATE clientes SET nome=?, cpf=?, endereco=?, senha=?, role=? WHERE id=?"; p=(self.nome, self.cpf, self.endereco, self._senha_plana, self.role, self.id); r=self.db.execute_query(q,p); return r is not None
        else: # INSERT
            q="INSERT INTO clientes (nome, cpf, endereco, senha, role) VALUES (?, ?, ?, ?, ?)"; p=(self.nome, self.cpf, self.endereco, self._senha_plana, self.role); new_id=self.db.execute_query(q,p);
            if new_id: self.id=new_id; return True
            print(f"Falha ao inserir cliente CPF {self.cpf}."); return False # Pode ser CPF duplicado

    def check_password(self, password_attempt: str) -> bool:
        """Verifica se a senha fornecida corresponde à senha armazenada."""
        if not self._senha_plana: print("Debug: Tentando verificar senha, mas _senha_plana está vazia/None."); return False
        # **AVISO:** Comparação insegura! Use hashing.
        resultado = (password_attempt == self._senha_plana)
        return resultado

    def delete(self) -> bool:
        """Exclui o cliente do banco de dados (CASCADE deve excluir contas/transações)."""
        if self.id is None: return False; q="DELETE FROM clientes WHERE id = ?"; r=self.db.execute_query(q, (self.id,));
        if r is not None: self.id=None; return True; return False

    @staticmethod
    def find_by_cpf(db_manager: DatabaseManager, cpf: str) -> 'Cliente | None':
        """Busca um cliente pelo CPF no BD (incluindo senha e papel)."""
        data = db_manager.fetch_one("SELECT id, nome, cpf, endereco, senha, role FROM clientes WHERE cpf = ?", (cpf,))
        if data: # Mapeia manualmente 'id' do BD para 'cliente_id' do construtor
            return Cliente(db_manager, cliente_id=data['id'], nome=data['nome'], cpf=data['cpf'], endereco=data['endereco'], senha=data['senha'], role=data['role'])
        return None

    def __str__(self):
        """Representação em string do objeto Cliente."""
        id_str=f" (ID: {self.id})" if self.id else ""; role_str=f" [{self.role}]" if self.role else "";
        return f"Cliente: {self.nome} (CPF: {self.cpf}){role_str}{id_str}"

class Conta:
    """Classe base para contas bancárias, interagindo com o BD."""
    # Definição de atributos para clareza
    id: int | None = None; numero: str | None = None; agencia: str | None = None
    _saldo: float = 0.0; cliente_id: int | None = None; tipo_conta: str | None = None
    limite: float = 0.0; limite_saques: int = 3; _cliente_cache: Cliente | None = None

    def __init__(self, db_manager: DatabaseManager, conta_id: int | None = None):
        self.db = db_manager
        if conta_id is not None: self.id = conta_id; self._load_from_db()
        else: print("Alerta: Conta inicializada sem ID.")

    def _load_from_db(self):
        """Carrega os dados da conta do BD usando o ID."""
        if self.id is None: return
        data = self.db.fetch_one("SELECT * FROM contas WHERE id = ?", (self.id,))
        if data:
            self.numero, self.agencia, self._saldo = data['numero'], data['agencia'], data['saldo']
            self.limite, self.limite_saques = data['limite'], data['limite_saques']
            self.tipo_conta, self.cliente_id = data['tipo_conta'], data['cliente_id']
            self._cliente_cache = None # Limpa cache do cliente ao recarregar
        else: print(f"Erro: Conta ID {self.id} não encontrada."); self.id = None # Invalida

    @property
    def saldo(self) -> float:
        """Retorna o saldo atual (mantido em memória após carregamento/operações)."""
        return self._saldo

    @property
    def cliente(self) -> Cliente | None:
        """Retorna o objeto Cliente associado (busca no BD com cache)."""
        if self._cliente_cache is None and self.cliente_id is not None:
            self._cliente_cache = Cliente(self.db, cliente_id=self.cliente_id) # Carrega cliente
            if not self._cliente_cache or not self._cliente_cache.id: self._cliente_cache = None # Verifica se carregou
        return self._cliente_cache

    @property
    def historico(self) -> list[dict]:
        """Busca as transações da conta no BD."""
        if self.id is None: return []
        q = "SELECT id, tipo, valor, timestamp, conta_destino_id FROM transacoes WHERE conta_id = ? ORDER BY timestamp ASC"
        res = self.db.fetch_all(q, (self.id,)); return [dict(row) for row in res] # Retorna lista de dicionários

    def _get_numero_saques_hoje(self) -> int:
        """Consulta o BD para saber quantos saques/transferências foram feitos hoje."""
        if self.id is None: return 0
        hoje = datetime.date.today().strftime('%Y-%m-%d')
        q = "SELECT COUNT(*) as total FROM transacoes WHERE conta_id = ? AND tipo IN ('saque', 'transferencia_enviada') AND DATE(timestamp) = ?"
        res = self.db.fetch_one(q, (self.id, hoje)); return res['total'] if res else 0

    def _atualizar_saldo_e_registrar_transacao(self, tipo: str, valor: float, conta_destino_id: int | None = None) -> bool:
        """Método interno ATUALIZADO para transações atômicas (deposito, saque, transferencia)."""
        if self.id is None: return False
        conn = None
        try:
            conn = self.db._connect(); cursor = conn.cursor()
            # --- Início da Transação Atômica ---
            cursor.execute("SELECT saldo FROM contas WHERE id = ?", (self.id,)) # Saldo Origem
            saldo_origem_db = cursor.fetchone()['saldo']; novo_saldo_origem = saldo_origem_db

            if tipo == 'deposito': novo_saldo_origem = saldo_origem_db + valor
            elif tipo in ('saque', 'transferencia_enviada'):
                saldo_disponivel = saldo_origem_db
                if isinstance(self, ContaCorrente): saldo_disponivel += self.limite
                if valor > saldo_disponivel: conn.rollback(); print(f"BD Check: Saldo insuficiente para {tipo}."); return False
                novo_saldo_origem = saldo_origem_db - valor
                if tipo == 'transferencia_enviada': # Lógica da transferência
                    if conta_destino_id is None: conn.rollback(); return False
                    cursor.execute("SELECT saldo FROM contas WHERE id = ?", (conta_destino_id,)) # Saldo Destino
                    saldo_destino_row = cursor.fetchone()
                    if saldo_destino_row is None: conn.rollback(); print("Conta destino não existe."); return False
                    novo_saldo_destino = saldo_destino_row['saldo'] + valor
                    cursor.execute("UPDATE contas SET saldo = ? WHERE id = ?", (novo_saldo_destino, conta_destino_id)) # Atualiza Destino
                    cursor.execute("INSERT INTO transacoes (conta_id, tipo, valor, conta_destino_id) VALUES (?, ?, ?, ?)", (conta_destino_id, 'transferencia_recebida', valor, self.id)) # Registra Recebimento
            else: conn.rollback(); return False # Tipo inválido

            cursor.execute("UPDATE contas SET saldo = ? WHERE id = ?", (novo_saldo_origem, self.id)) # Atualiza Origem
            cursor.execute("INSERT INTO transacoes (conta_id, tipo, valor, conta_destino_id) VALUES (?, ?, ?, ?)", (self.id, tipo, valor, conta_destino_id if tipo == 'transferencia_enviada' else None)) # Registra Origem
            conn.commit() # Confirma TUDO
            # --- Fim da Transação Atômica ---
            self._saldo = novo_saldo_origem; print(f"{tipo.replace('_', ' ').capitalize()} R$ {valor:.2f} OK no BD."); return True
        except sqlite3.Error as e:
            print(f"Erro BD durante {tipo}: {e}");
            if conn: conn.rollback(); messagebox.showerror("Erro BD", f"Falha ao processar {tipo}.")
            return False
        finally:
            if conn: conn.close()

    def depositar(self, valor: float) -> bool:
        """Realiza um depósito."""
        if self.id is None: messagebox.showerror("Erro", "Conta inválida."); return False
        if valor <= 0: messagebox.showerror("Erro Depósito", "Valor deve ser positivo."); return False
        return self._atualizar_saldo_e_registrar_transacao('deposito', valor)

    def sacar(self, valor: float) -> bool:
        """Realiza um saque (validação inicial + transação BD)."""
        if self.id is None: messagebox.showerror("Erro", "Conta inválida."); return False
        if valor <= 0: messagebox.showerror("Erro Saque", "Valor deve ser positivo."); return False
        saldo_disp = self.saldo
        # Validação inicial rápida (sem limite para conta base)
        if not isinstance(self, ContaCorrente) and valor > saldo_disp:
             messagebox.showerror("Erro Saque", f"Saldo insuficiente: R$ {saldo_disp:.2f}"); return False
        # Validação de limite diário para CC (inclui transferências)
        if isinstance(self, ContaCorrente):
            num_saques_hoje = self._get_numero_saques_hoje()
            if num_saques_hoje >= self.limite_saques:
                messagebox.showwarning("Limite", f"Limite de {self.limite_saques} saques/transferências diários atingido."); return False
            # Validação inicial rápida com limite para CC
            saldo_disp += self.limite
            if valor > saldo_disp: messagebox.showerror("Erro Saque", f"Saldo+Limite insuficiente: R$ {saldo_disp:.2f}"); return False
        # Transação BD (com validação final de saldo/limite)
        return self._atualizar_saldo_e_registrar_transacao('saque', valor)

    def transferir(self, valor: float, conta_destino: 'Conta') -> bool:
        """Realiza uma transferência para outra conta de forma atômica."""
        if not (self.id and conta_destino and conta_destino.id): messagebox.showerror("Erro", "Conta de origem ou destino inválida."); return False
        if self.id == conta_destino.id: messagebox.showerror("Erro", "Contas de origem e destino iguais."); return False
        if valor <= 0: messagebox.showerror("Erro Transferência", "Valor deve ser positivo."); return False
        # Validação inicial saldo/limite
        saldo_disp = self.saldo
        if isinstance(self, ContaCorrente): saldo_disp += self.limite
        if valor > saldo_disp: messagebox.showerror("Erro Transferência", f"Saldo/Limite insuficiente: R$ {saldo_disp:.2f}"); return False
        # Validação limite diário
        if isinstance(self, ContaCorrente):
            num_saques_hoje = self._get_numero_saques_hoje()
            if num_saques_hoje >= self.limite_saques:
                messagebox.showwarning("Limite", f"Limite de {self.limite_saques} saques/transferências diários atingido."); return False
        # Transação BD (com validação final)
        return self._atualizar_saldo_e_registrar_transacao('transferencia_enviada', valor, conta_destino.id)

    def exibir_extrato(self) -> str:
        """Gera string formatada do extrato (com detalhes de transferência)."""
        cliente = self.cliente
        if not self.id or not cliente: return "Erro: Conta/Cliente não carregados."
        transacoes_lista = self.historico
        extrato_str = f"""
        ================ EXTRATO ================
        {str(cliente)}
        Agência: {self.agencia}  Conta: {self.numero} ({self.tipo_conta.capitalize()})
        -----------------------------------------
        Transações:
        """
        if not transacoes_lista: transacoes_str = "Nenhuma movimentação realizada."
        else:
            linhas_transacoes = []
            for t in transacoes_lista:
                try: ts_str=t['timestamp'].split('.')[0]; ts=datetime.datetime.strptime(ts_str,'%Y-%m-%d %H:%M:%S'); ts_fmt=ts.strftime('%d/%m/%Y %H:%M:%S')
                except: ts_fmt = t['timestamp']
                valor_fmt = f"R$ {t['valor']:.2f}"; tipo = t['tipo']; detalhe = ""
                if tipo == 'deposito': tipo_fmt = "Depósito".ljust(18); op = "+" # Aumentado ljust
                elif tipo == 'saque': tipo_fmt = "Saque".ljust(18); op = "-"
                elif tipo == 'transferencia_enviada':
                    tipo_fmt = "Transf. Enviada".ljust(18); op = "-"
                    if t['conta_destino_id']: detalhe = f" -> ID:{t['conta_destino_id']}" # Mostra ID destino
                elif tipo == 'transferencia_recebida':
                    tipo_fmt = "Transf. Recebida".ljust(18); op = "+"
                    if t['conta_destino_id']: detalhe = f" <- ID:{t['conta_destino_id']}" # ID aqui é a origem
                else: tipo_fmt = tipo.capitalize().ljust(18); op = "?"
                linhas_transacoes.append(f"{ts_fmt} - {tipo_fmt}: {op} {valor_fmt}{detalhe}")
            transacoes_str = "\n".join(linhas_transacoes)
        extrato_str += f"\n{textwrap.indent(transacoes_str, '  ')}\n"
        extrato_str += f"-----------------------------------------\n"
        saldo_atual_db = self.db.fetch_one("SELECT saldo FROM contas WHERE id = ?", (self.id,));
        if saldo_atual_db: self._saldo = saldo_atual_db['saldo']; extrato_str += f"Saldo Atual: R$ {self.saldo:.2f}\n"
        else: extrato_str += f"Saldo Atual: Erro\n"
        if isinstance(self, ContaCorrente): extrato_str += f"Limite Ch. Especial: R$ {self.limite:.2f}\n"
        extrato_str += "=========================================\n"
        return extrato_str

class ContaCorrente(Conta):
    """Conta Corrente, herda de Conta."""
    pass # Lógica específica já tratada na classe base ou herdada

# --- PARTE 2: Tela de Login ---

class LoginWindow(customtkinter.CTk):
    """Janela de login inicial da aplicação."""
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(); self.db = db_manager; self.title("Login - Banco Moderno"); self.geometry("400x350"); self.resizable(False, False); self.grid_columnconfigure(0, weight=1)
        self.lbl_title = customtkinter.CTkLabel(self, text="Acesso ao Sistema", font=customtkinter.CTkFont(size=20, weight="bold")); self.lbl_title.grid(row=0, column=0, padx=20, pady=(30, 15))
        self.lbl_cpf = customtkinter.CTkLabel(self, text="CPF (xxx.xxx.xxx-xx):"); self.lbl_cpf.grid(row=1, column=0, padx=50, pady=(10, 0), sticky="w")
        self.entry_cpf = customtkinter.CTkEntry(self, width=300); self.entry_cpf.grid(row=2, column=0, padx=50, pady=(0, 10), sticky="ew")
        self.lbl_senha = customtkinter.CTkLabel(self, text="Senha:"); self.lbl_senha.grid(row=3, column=0, padx=50, pady=(10, 0), sticky="w")
        self.entry_senha = customtkinter.CTkEntry(self, width=300, show="*"); self.entry_senha.grid(row=4, column=0, padx=50, pady=(0, 15), sticky="ew")
        self.btn_login = customtkinter.CTkButton(self, text="Login", command=self.attempt_login, width=300); self.btn_login.grid(row=5, column=0, padx=50, pady=10)
        self.lbl_error = customtkinter.CTkLabel(self, text="", text_color="red"); self.lbl_error.grid(row=6, column=0, padx=50, pady=(5, 10))
        self.entry_cpf.focus(); self.entry_senha.bind("<Return>", self.attempt_login); self.btn_login.bind("<Return>", self.attempt_login)

    def attempt_login(self, event=None):
        """Tenta autenticar o usuário."""
        cpf = self.entry_cpf.get().strip(); senha = self.entry_senha.get()
        if not cpf or not senha: self.show_error("CPF e Senha obrigatórios."); return
        cliente_logando = Cliente.find_by_cpf(self.db, cpf) # Usa método corrigido
        if cliente_logando and cliente_logando.check_password(senha):
            print(f"Login OK: {cliente_logando}"); self.destroy(); main_app = BancoGUI(self.db, cliente_logando, cliente_logando.role); main_app.mainloop()
        else: self.show_error("CPF ou Senha inválidos."); self.entry_senha.delete(0, tk.END)

    def show_error(self, message):
        """Exibe mensagem de erro no login."""
        self.lbl_error.configure(text=message)

# --- PARTE 3: Interface Gráfica Principal (Traduzida e com Transferência) ---

class BancoGUI(customtkinter.CTk):
    """Interface gráfica principal, adaptada para login, papel e transferência."""
    def __init__(self, db_manager: DatabaseManager, logged_in_cliente: Cliente, user_role: str):
        super().__init__(); self.db = db_manager; self.logged_in_cliente = logged_in_cliente; self.user_role = user_role
        self.conta_selecionada: Conta | None = None; self.map_display_to_conta_id: dict[str, int] = {}
        self.proximo_numero_conta = self._get_next_account_number()

        # Config Janela e Aparência
        customtkinter.set_appearance_mode("System"); customtkinter.set_default_color_theme("blue")
        self.title(f"Banco App - [{user_role.upper()}] {logged_in_cliente.nome}") # Título com nome e papel
        self.geometry("800x850")

        # Layout Principal
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(3, weight=1); self.grid_rowconfigure(4, weight=0)

        # --- Frame Superior ---
        top_frame = customtkinter.CTkFrame(self, fg_color="transparent"); top_frame.grid(row=0, column=0, padx=20, pady=(10, 5), sticky="ew"); top_frame.grid_columnconfigure(1, weight=1)
        self.title_label = customtkinter.CTkLabel(top_frame, text="Bem-vindo(a)!", font=customtkinter.CTkFont(size=20, weight="bold")); self.title_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.account_options = ["Carregando..."]; self.selected_account_var = customtkinter.StringVar(value=self.account_options[0])
        self.account_dropdown = customtkinter.CTkOptionMenu(top_frame, variable=self.selected_account_var, command=self.selecionar_conta_pelo_dropdown, width=250, state="disabled"); self.account_dropdown.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.theme_switch = customtkinter.CTkSwitch(top_frame, text="Modo Escuro", command=self.toggle_theme); self.theme_switch.grid(row=0, column=2, padx=10, pady=5, sticky="e")
        if customtkinter.get_appearance_mode() == "Dark": self.theme_switch.select()

        # --- Frame Botões Gerenciamento ---
        self.mgmt_button_frame = customtkinter.CTkFrame(self, fg_color="transparent"); self.mgmt_button_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew"); self.mgmt_button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.btn_encerrar_conta = customtkinter.CTkButton(self.mgmt_button_frame, text="Encerrar Conta Sel.", command=self.encerrar_conta_selecionada, fg_color="#E57373", hover_color="#EF5350"); self.btn_encerrar_conta.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        if self.user_role == 'admin': # Botões exclusivos do Admin
            self.btn_add_conta = customtkinter.CTkButton(self.mgmt_button_frame, text="Add Conta p/ Cliente", command=self.adicionar_nova_conta_para_cliente); self.btn_add_conta.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
            self.btn_cadastrar_cliente = customtkinter.CTkButton(self.mgmt_button_frame, text="Cadastrar Cliente", command=self.abrir_janela_cadastro); self.btn_cadastrar_cliente.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
            self.btn_excluir_cliente = customtkinter.CTkButton(self.mgmt_button_frame, text="Excluir Cliente Sel.", command=self.excluir_cliente_selecionado, fg_color="#D32F2F", hover_color="#B71C1C"); self.btn_excluir_cliente.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        else: self.mgmt_button_frame.grid_columnconfigure(0, weight=4) # Botão de encerrar ocupa mais espaço

        # --- Frame Principal Conteúdo ---
        main_content_frame = customtkinter.CTkFrame(self, corner_radius=10); main_content_frame.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew"); main_content_frame.grid_columnconfigure(0, weight=1); main_content_frame.grid_rowconfigure(3, weight=1)
        # Seção Informações
        info_frame = customtkinter.CTkFrame(main_content_frame); info_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ew"); info_frame.grid_columnconfigure(1, weight=1)
        self.lbl_cliente = customtkinter.CTkLabel(info_frame, text="Cliente: -", anchor="w"); self.lbl_cliente.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        self.lbl_conta = customtkinter.CTkLabel(info_frame, text="Conta: -", anchor="w"); self.lbl_conta.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        self.lbl_saldo_texto = customtkinter.CTkLabel(info_frame, text="Saldo Atual:", font=customtkinter.CTkFont(size=14, weight="bold"), anchor="w"); self.lbl_saldo_texto.grid(row=2, column=0, padx=10, pady=(10, 10), sticky="w")
        self.lbl_saldo_valor = customtkinter.CTkLabel(info_frame, text="R$ -", font=customtkinter.CTkFont(size=16, weight="bold"), anchor="e"); self.lbl_saldo_valor.grid(row=2, column=1, padx=10, pady=(10, 10), sticky="e")
        # Seção Operações (Depósito/Saque)
        self.actions_frame = customtkinter.CTkFrame(main_content_frame); self.actions_frame.grid(row=1, column=0, padx=15, pady=5, sticky="ew"); self.actions_frame.grid_columnconfigure((1, 2, 3), weight=1)
        valor_label = customtkinter.CTkLabel(self.actions_frame, text="Valor Op:"); valor_label.grid(row=0, column=0, padx=(10, 0), pady=5, sticky="w")
        self.entry_valor = customtkinter.CTkEntry(self.actions_frame, placeholder_text="0.00", width=140); self.entry_valor.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.btn_depositar = customtkinter.CTkButton(self.actions_frame, text="Depositar", command=self.realizar_deposito); self.btn_depositar.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self.btn_sacar = customtkinter.CTkButton(self.actions_frame, text="Sacar", command=self.realizar_saque, fg_color="#E53935", hover_color="#C62828"); self.btn_sacar.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        # Seção Transferência
        self.transfer_frame = customtkinter.CTkFrame(main_content_frame); self.transfer_frame.grid(row=2, column=0, padx=15, pady=5, sticky="ew"); self.transfer_frame.grid_columnconfigure(1, weight=1); self.transfer_frame.grid_columnconfigure(3, weight=1); self.transfer_frame.grid_columnconfigure(4, weight=1)
        lbl_conta_dest = customtkinter.CTkLabel(self.transfer_frame, text="Conta Destino:"); lbl_conta_dest.grid(row=0, column=0, padx=(10,0), pady=5, sticky="w")
        self.entry_conta_destino = customtkinter.CTkEntry(self.transfer_frame, placeholder_text="Número", width=100); self.entry_conta_destino.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        lbl_valor_transf = customtkinter.CTkLabel(self.transfer_frame, text="Valor Transf:"); lbl_valor_transf.grid(row=0, column=2, padx=(10,0), pady=5, sticky="w")
        self.entry_valor_transferencia = customtkinter.CTkEntry(self.transfer_frame, placeholder_text="0.00", width=100); self.entry_valor_transferencia.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.btn_transferir = customtkinter.CTkButton(self.transfer_frame, text="Transferir", command=self.realizar_transferencia, fg_color="#0B5ED7", hover_color="#0A58CA"); self.btn_transferir.grid(row=0, column=4, padx=(5,10), pady=5, sticky="ew")
        # Seção Extrato
        self.extrato_frame = customtkinter.CTkFrame(main_content_frame); self.extrato_frame.grid(row=3, column=0, padx=15, pady=10, sticky="nsew"); self.extrato_frame.grid_rowconfigure(0, weight=1); self.extrato_frame.grid_columnconfigure(0, weight=1)
        self.txt_extrato = customtkinter.CTkTextbox(self.extrato_frame, wrap=tk.WORD, font=("Courier New", 11), corner_radius=8, border_width=1); self.txt_extrato.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew"); self.txt_extrato.configure(state="disabled")
        self.btn_atualizar_extrato = customtkinter.CTkButton(main_content_frame, text="Atualizar Extrato", command=self.mostrar_extrato, fg_color="grey", hover_color="#555555"); self.btn_atualizar_extrato.grid(row=4, column=0, padx=15, pady=(5, 10), sticky="ew")

        # --- Rodapé ---
        footer_label = customtkinter.CTkLabel(self, text="Artur Kuzma Marques fez isso :)", font=customtkinter.CTkFont(size=10), text_color="gray"); footer_label.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="s")

        # --- Inicialização da Interface ---
        self.after(100, self.carregar_e_atualizar_contas_iniciais) # Carrega dados após janela aparecer

    def _get_next_account_number(self) -> int:
        """Busca o maior número de conta no BD e retorna o próximo."""
        max_num_row = self.db.fetch_one("SELECT MAX(CAST(numero AS INTEGER)) as max_num FROM contas")
        max_num = 1000;
        if max_num_row and max_num_row['max_num'] is not None:
            try: max_num = int(max_num_row['max_num'])
            except ValueError: pass
        return max_num + 1

    # --- Funções de Gerenciamento e Callbacks (comentários traduzidos) ---

    def carregar_e_atualizar_contas_iniciais(self):
        """Carrega contas do BD (filtradas por papel) e atualiza dropdown."""
        print("Carregando contas iniciais do BD..."); self.atualizar_dropdown_contas()
        if self.account_options and "Nenhuma conta" not in self.account_options[0] and "Você não possui contas" not in self.account_options[0]:
            self.selected_account_var.set(self.account_options[0]); self.selecionar_conta_pelo_dropdown(self.account_options[0])
        else: self.atualizar_info_display()

    def atualizar_dropdown_contas(self):
        """Busca contas no BD (filtrando por user se não for admin) e atualiza."""
        print(f"Atualizando dropdown (Papel: {self.user_role})..."); contas_db=[]; query=""; params=()
        if self.user_role=='admin': q="SELECT co.id, co.numero, cl.nome FROM contas co JOIN clientes cl ON co.cliente_id = cl.id ORDER BY cl.nome, co.numero ASC"
        elif self.user_role=='user' and self.logged_in_cliente and self.logged_in_cliente.id: q="SELECT co.id, co.numero, cl.nome FROM contas co JOIN clientes cl ON co.cliente_id = cl.id WHERE co.cliente_id = ? ORDER BY co.numero ASC"; params=(self.logged_in_cliente.id,)
        else: print("Erro: Papel/Login inválido.")
        if q: contas_db = self.db.fetch_all(q, params)
        self.map_display_to_conta_id.clear(); self.account_options = []
        if not contas_db:
            if self.user_role=='user': self.account_options=["Você não possui contas"]
            else: self.account_options=["Nenhuma conta cadastrada"]
            self.conta_selecionada=None; self.selected_account_var.set(self.account_options[0]); self.account_dropdown.configure(values=self.account_options, state="disabled")
        else:
            for r in contas_db: self.account_options.append(f"{r['nome']} (Conta {r['numero']})"); self.map_display_to_conta_id[self.account_options[-1]]=r['id']
            self.account_dropdown.configure(values=self.account_options, state="normal")
            c_id_ant=self.conta_selecionada.id if self.conta_selecionada else None; sel_enc=False
            if c_id_ant is not None:
                for disp, c_id in self.map_display_to_conta_id.items():
                    if c_id == c_id_ant: self.selected_account_var.set(disp); sel_enc=True; break
            if not sel_enc:
                prim_op=self.account_options[0]; self.selected_account_var.set(prim_op)
                c_id_prim=self.map_display_to_conta_id.get(prim_op)
                if c_id_prim: self.conta_selecionada = ContaCorrente(self.db, conta_id=c_id_prim)
                else: self.conta_selecionada = None
        self.atualizar_info_display() # Atualiza UI com base na nova lista/seleção

    def selecionar_conta_pelo_dropdown(self, selection_string: str):
        """Callback quando uma conta é selecionada no dropdown."""
        print(f"Dropdown selecionado: {selection_string}");
        if "Nenhuma conta" in selection_string or "Você não possui contas" in selection_string: self.conta_selecionada = None
        else:
            conta_id = self.map_display_to_conta_id.get(selection_string)
            if conta_id:
                temp_conta = ContaCorrente(self.db, conta_id=conta_id)
                if not temp_conta.id: messagebox.showerror("Erro", f"Falha ao carregar conta ID {conta_id}."); self.conta_selecionada = None
                elif self.user_role=='admin' or (temp_conta.cliente and temp_conta.cliente.id == self.logged_in_cliente.id): self.conta_selecionada = temp_conta # Seleção válida
                else: messagebox.showerror("Acesso Negado", "Permissão negada."); self.conta_selecionada = None # Impede seleção de conta de outro user
            else: messagebox.showerror("Erro Interno", f"ID não encontrado: {selection_string}"); self.conta_selecionada = None
        self.atualizar_info_display() # Atualiza UI com a nova seleção

    def atualizar_info_display(self):
        """Atualiza labels, extrato e estados de botões com base na conta_selecionada."""
        has_selection = self.conta_selecionada and self.conta_selecionada.id; is_admin = self.user_role == 'admin'
        op_state = "normal" if has_selection else "disabled"
        # Botões/Entries de Operação e Transferência
        self.entry_valor.configure(state=op_state); self.btn_depositar.configure(state=op_state); self.btn_sacar.configure(state=op_state); self.btn_atualizar_extrato.configure(state=op_state)
        self.entry_conta_destino.configure(state=op_state); self.entry_valor_transferencia.configure(state=op_state); self.btn_transferir.configure(state=op_state)
        # Botão Encerrar Conta
        self.btn_encerrar_conta.configure(state=op_state)
        # Botões Admin (só existem se for admin)
        if is_admin: self.btn_add_conta.configure(state=op_state); self.btn_excluir_cliente.configure(state=op_state); self.btn_cadastrar_cliente.configure(state="normal")
        # Labels e Extrato
        if has_selection:
            conta = self.conta_selecionada; cliente = conta.cliente
            if cliente: self.lbl_cliente.configure(text=f"Cliente: {cliente.nome} (CPF: {cliente.cpf})")
            else: self.lbl_cliente.configure(text="Cliente: Erro")
            self.lbl_conta.configure(text=f"Conta: {conta.agencia}-{conta.numero} ({conta.tipo_conta.capitalize()})")
            self.atualizar_display_saldo(); self.mostrar_extrato()
        else: # Sem seleção
            self.lbl_cliente.configure(text="Cliente: -"); self.lbl_conta.configure(text="Conta: -")
            self.lbl_saldo_valor.configure(text="R$ -"); self.atualizar_cor_saldo()
            self.txt_extrato.configure(state="normal"); self.txt_extrato.delete("1.0", tk.END); self.txt_extrato.insert("1.0", "Selecione uma conta."); self.txt_extrato.configure(state="disabled")

    def abrir_janela_cadastro(self):
        """Abre janela para cadastrar novo cliente (Admin)."""
        if hasattr(self, 'cadastro_window') and self.cadastro_window.winfo_exists(): self.cadastro_window.focus(); return
        self.cadastro_window = customtkinter.CTkToplevel(self); self.cadastro_window.title("Cadastrar Novo Cliente"); self.cadastro_window.geometry("400x350"); self.cadastro_window.transient(self); self.cadastro_window.grab_set(); self.cadastro_window.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(self.cadastro_window, text="Nome:").grid(row=0, column=0, padx=10, pady=10, sticky="w"); entry_nome = customtkinter.CTkEntry(self.cadastro_window, width=250); entry_nome.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        customtkinter.CTkLabel(self.cadastro_window, text="CPF:").grid(row=1, column=0, padx=10, pady=10, sticky="w"); entry_cpf = customtkinter.CTkEntry(self.cadastro_window, width=250); entry_cpf.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        customtkinter.CTkLabel(self.cadastro_window, text="Endereço:").grid(row=2, column=0, padx=10, pady=10, sticky="w"); entry_endereco = customtkinter.CTkEntry(self.cadastro_window, width=250); entry_endereco.grid(row=2, column=1, padx=10, pady=10, sticky="ew")
        customtkinter.CTkLabel(self.cadastro_window, text="Senha:").grid(row=3, column=0, padx=10, pady=10, sticky="w"); entry_senha = customtkinter.CTkEntry(self.cadastro_window, width=250, show="*"); entry_senha.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
        btn_confirmar = customtkinter.CTkButton(self.cadastro_window, text="Confirmar Cadastro", command=lambda: self.cadastrar_cliente(entry_nome.get(), entry_cpf.get(), entry_endereco.get(), entry_senha.get(), self.cadastro_window)); btn_confirmar.grid(row=4, column=0, columnspan=2, padx=20, pady=20, sticky="ew"); entry_nome.focus()

    def cadastrar_cliente(self, nome, cpf, endereco, senha, window_ref):
        """Valida e salva novo cliente e conta inicial no BD (Admin)."""
        # (Ordem corrigida: messagebox e destroy ANTES de atualizar UI)
        nome, cpf, endereco, senha = nome.strip(), cpf.strip(), endereco.strip(), senha
        if not nome or not cpf or not endereco or not senha: messagebox.showerror("Erro", "Todos campos obrigatórios!", parent=window_ref); return
        if len(cpf) != 14 or cpf[3]!='.' or cpf[7]!='.' or cpf[11]!='-': messagebox.showerror("Erro", "Formato CPF inválido.", parent=window_ref); return
        if Cliente.find_by_cpf(self.db, cpf): messagebox.showerror("Erro", f"CPF {cpf} já cadastrado!", parent=window_ref); return
        novo_cliente = Cliente(self.db, nome=nome, cpf=cpf, endereco=endereco, senha=senha, role='user')
        if novo_cliente.save():
            cliente_id_criado = novo_cliente.id; print(f"Cliente {nome} (ID: {cliente_id_criado}) salvo.")
            while True: 
                numero_nova_conta = str(self.proximo_numero_conta); self.proximo_numero_conta += 1
                if not self.db.fetch_one("SELECT id FROM contas WHERE numero = ?", (numero_nova_conta,)): break
            conta_id_criado = self.db.execute_query("INSERT INTO contas (numero, cliente_id) VALUES (?, ?)", (numero_nova_conta, cliente_id_criado))
            if conta_id_criado:
                print(f"Conta {numero_nova_conta} criada.");
                messagebox.showinfo("Sucesso", f"Cliente {nome} cadastrado!\nConta {numero_nova_conta} criada.", parent=self) # Parent=self
                window_ref.destroy() # Destroi pop-up
                self.atualizar_dropdown_contas() # Atualiza lista principal
                if self.user_role == 'admin': # Seleciona nova conta se for admin
                     sel_str = f"{nome} (Conta {numero_nova_conta})";
                     if sel_str in self.map_display_to_conta_id: self.selected_account_var.set(sel_str); self.selecionar_conta_pelo_dropdown(sel_str)
            else: messagebox.showerror("Erro BD", "Cliente salvo, falha ao criar conta.", parent=window_ref); novo_cliente.delete(); self.atualizar_dropdown_contas()
        else: messagebox.showerror("Erro BD", "Falha ao salvar cliente.", parent=window_ref)

    def adicionar_nova_conta_para_cliente(self):
        """(Admin) Adiciona uma nova conta corrente para o cliente selecionado."""
        if not self.conta_selecionada or not self.conta_selecionada.cliente: messagebox.showerror("Erro", "Selecione conta do cliente."); return
        cliente_alvo = self.conta_selecionada.cliente
        if not cliente_alvo or not cliente_alvo.id: messagebox.showerror("Erro", "Cliente selecionado inválido."); return
        confirm = messagebox.askyesno("Adicionar Conta", f"Criar nova conta para {cliente_alvo.nome}?", parent=self)
        if confirm:
            while True: 
                numero_nova_conta = str(self.proximo_numero_conta); self.proximo_numero_conta += 1
                if not self.db.fetch_one("SELECT id FROM contas WHERE numero = ?", (numero_nova_conta,)): break
            conta_id_criado = self.db.execute_query("INSERT INTO contas (numero, cliente_id) VALUES (?, ?)", (numero_nova_conta, cliente_alvo.id))
            if conta_id_criado:
                messagebox.showinfo("Sucesso", f"Nova conta {numero_nova_conta} criada para {cliente_alvo.nome}."); self.atualizar_dropdown_contas()
                sel_str = f"{cliente_alvo.nome} (Conta {numero_nova_conta})"
                if sel_str in self.map_display_to_conta_id: self.selected_account_var.set(sel_str); self.selecionar_conta_pelo_dropdown(sel_str)
            else: messagebox.showerror("Erro BD", "Falha ao criar nova conta.")

    def encerrar_conta_selecionada(self):
        """Encerra (exclui) a conta selecionada (com verificação de permissão)."""
        if not self.conta_selecionada or not self.conta_selecionada.id: messagebox.showerror("Erro", "Nenhuma conta selecionada."); return
        conta_a_encerrar = self.conta_selecionada; cliente_dono = conta_a_encerrar.cliente
        permitido = (self.user_role == 'admin') or (self.user_role == 'user' and cliente_dono and cliente_dono.id == self.logged_in_cliente.id)
        if not permitido: messagebox.showerror("Acesso Negado", "Permissão negada."); return
        confirm = messagebox.askyesno("Confirmar", f"Encerrar conta {conta_a_encerrar.numero} de {cliente_dono.nome if cliente_dono else 'N/A'}?", icon='warning', parent=self)
        if confirm:
            q = "DELETE FROM contas WHERE id = ?"; r = self.db.execute_query(q, (conta_a_encerrar.id,))
            if r is not None: messagebox.showinfo("Sucesso", f"Conta {conta_a_encerrar.numero} encerrada."); self.conta_selecionada = None; self.atualizar_dropdown_contas()
            else: messagebox.showerror("Erro BD", f"Falha ao encerrar conta {conta_a_encerrar.numero}.")

    def excluir_cliente_selecionado(self):
        """(Admin) Exclui o cliente selecionado e seus dados."""
        if not self.conta_selecionada or not self.conta_selecionada.cliente: messagebox.showerror("Erro", "Selecione conta do cliente."); return
        cliente_para_excluir = self.conta_selecionada.cliente
        if not cliente_para_excluir.id: messagebox.showerror("Erro", "Cliente inválido."); return
        if cliente_para_excluir.cpf == "000.000.000-00": messagebox.showerror("Inválido", "ADMIN padrão não pode ser excluído."); return
        confirm = messagebox.askyesno("Confirmar", f"Excluir cliente {cliente_para_excluir.nome}?\n\nCONTAS E TRANSAÇÕES SERÃO PERDIDAS!", icon='warning', parent=self)
        if confirm:
            if cliente_para_excluir.delete(): messagebox.showinfo("Sucesso", f"Cliente {cliente_para_excluir.nome} excluído."); self.conta_selecionada = None; self.atualizar_dropdown_contas()
            else: messagebox.showerror("Erro BD", f"Falha ao excluir cliente {cliente_para_excluir.nome}.")

    def _obter_valor_transferencia(self) -> float | None:
        """Obtém e valida o valor do campo de transferência."""
        try:
            valor_str = self.entry_valor_transferencia.get().replace(",", ".")
            if not valor_str: messagebox.showwarning("Inválido", "Insira valor para transferir."); return None
            valor = float(valor_str)
            if valor <= 0: messagebox.showerror("Erro", "Valor da transferência positivo."); return None
            return valor
        except ValueError: messagebox.showerror("Erro", "Valor da transferência inválido."); return None

    def realizar_transferencia(self):
        """Executa a operação de transferência entre contas."""
        if not self.conta_selecionada or not self.conta_selecionada.id: messagebox.showerror("Erro", "Selecione conta origem."); return
        conta_origem = self.conta_selecionada
        num_conta_destino = self.entry_conta_destino.get().strip()
        valor = self._obter_valor_transferencia()
        if not num_conta_destino or valor is None: return # Erros já mostrados

        conta_destino_data = self.db.fetch_one("SELECT id FROM contas WHERE numero = ?", (num_conta_destino,))
        if not conta_destino_data: messagebox.showerror("Erro", f"Conta destino '{num_conta_destino}' não encontrada."); return
        conta_destino_id = conta_destino_data['id']
        conta_destino_obj = ContaCorrente(self.db, conta_id=conta_destino_id) # Cria obj temporário
        if not conta_destino_obj.id: messagebox.showerror("Erro", f"Falha ao carregar conta destino {num_conta_destino}."); return

        # Chama método transferir (lida com BD e validações finais)
        sucesso = conta_origem.transferir(valor, conta_destino_obj)
        if sucesso:
            messagebox.showinfo("Sucesso", f"Transferência R$ {valor:.2f} para conta {num_conta_destino} OK!")
            self.entry_conta_destino.delete(0, tk.END); self.entry_valor_transferencia.delete(0, tk.END) # Limpa campos
            self.atualizar_display_saldo(); self.mostrar_extrato() # Atualiza UI da origem

    # --- Funções de Callback Restantes (sem mudanças) ---
    def toggle_theme(self): customtkinter.set_appearance_mode("Dark" if self.theme_switch.get()==1 else "Light"); self.atualizar_cor_saldo()
    def atualizar_cor_saldo(self):
        if self.conta_selecionada and self.conta_selecionada.id: saldo=self.conta_selecionada.saldo; cVerde="#34A853"; cVermelho="#E53935"; cor=cVerde if saldo>=0 else cVermelho; self.lbl_saldo_valor.configure(text_color=cor)
        else: cPadrao=customtkinter.ThemeManager.theme["CTkLabel"]["text_color"]; self.lbl_saldo_valor.configure(text_color=cPadrao)
    def atualizar_display_saldo(self):
        if self.conta_selecionada and self.conta_selecionada.id: saldo=self.conta_selecionada.saldo; self.lbl_saldo_valor.configure(text=f"R$ {saldo:.2f}"); self.atualizar_cor_saldo()
        else: self.lbl_saldo_valor.configure(text="R$ -"); self.atualizar_cor_saldo()
    def mostrar_extrato(self):
        if not self.conta_selecionada or not self.conta_selecionada.id: return
        self.atualizar_display_saldo(); txt=self.conta_selecionada.exibir_extrato()
        self.txt_extrato.configure(state="normal"); self.txt_extrato.delete("1.0", tk.END); self.txt_extrato.insert("1.0", txt); self.txt_extrato.configure(state="disabled")
    def _obter_valor_entry(self) -> float | None:
        try:
            vStr=self.entry_valor.get().replace(",",".")
            if not vStr: messagebox.showwarning("Inválido", "Insira valor."); return None
            v=float(vStr)
            if v<=0: messagebox.showerror("Erro", "Valor positivo."); return None
            self.entry_valor.delete(0, tk.END); return v
        except ValueError: messagebox.showerror("Erro", "Valor numérico inválido."); return None
    def realizar_deposito(self):
        if not self.conta_selecionada or not self.conta_selecionada.id: messagebox.showerror("Erro", "Selecione conta."); return
        v = self._obter_valor_entry()
        if v is not None:
            if self.conta_selecionada.depositar(v): messagebox.showinfo("Sucesso", f"Depósito R$ {v:.2f} OK!"); self.atualizar_display_saldo(); self.mostrar_extrato()
    def realizar_saque(self):
        if not self.conta_selecionada or not self.conta_selecionada.id: messagebox.showerror("Erro", "Selecione conta."); return
        v = self._obter_valor_entry()
        if v is not None:
            if self.conta_selecionada.sacar(v): messagebox.showinfo("Sucesso", f"Saque R$ {v:.2f} OK!"); self.atualizar_display_saldo(); self.mostrar_extrato()

# --- PARTE 4: Execução Principal ---

if __name__ == "__main__":
    print("AVISO: Senhas em texto plano (INSEGURO!)")
    db_manager = DatabaseManager("banco_moderno_v6_ptbr.db") # Novo nome
    login_app = LoginWindow(db_manager)
    login_app.mainloop() # Inicia pela tela de login
    print("Aplicação finalizada.")