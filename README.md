# Sistema Bancário Moderno em Python com Tkinter e Banco de Dados SQLite

Este projeto implementa um sistema bancário completo utilizando a biblioteca Tkinter para a interface gráfica e o SQLite para o gerenciamento do banco de dados. Ele oferece funcionalidades como gerenciamento de clientes, contas, transações (depósitos, saques, transferências) e um sistema de login com suporte a diferentes níveis de acesso (usuário e administrador).

## Funcionalidades

* **Gerenciamento de Clientes:**
    * Cadastro de novos clientes (apenas para administradores).
    * Exclusão de clientes existentes (apenas para administradores).
    * Cada cliente possui nome, CPF, endereço, senha e papel (role).
* **Gerenciamento de Contas:**
    * Criação de novas contas para clientes (apenas para administradores).
    * Encerramento de contas.
    * As contas possuem número, agência, saldo, limite (para contas correntes), limite de saques diários e tipo (corrente).
* **Transações:**
    * Depósitos.
    * Saques.
    * Transferências entre contas (com validações de saldo e limites).
    * Histórico de transações para cada conta.
* **Interface Gráfica:**
    * Tela de login com autenticação de usuário.
    * Interface principal com:
        * Listagem de contas do cliente logado (ou de todos os clientes, para administradores).
        * Exibição de informações da conta selecionada (cliente, número, saldo).
        * Formulários para realizar depósitos, saques e transferências.
        * Extrato da conta.
        * Switch para alternar entre temas claro e escuro.
* **Segurança e Acesso:**
    * Sistema de login com verificação de CPF e senha.
    * Controle de acesso baseado em "role" (administrador ou usuário comum).
    * Administradores têm permissão para gerenciar clientes e contas, enquanto usuários comuns só podem acessar suas próprias contas.
* **Banco de Dados:**
    * Utilização do SQLite para armazenar dados de clientes, contas e transações.
    * Criação automática das tabelas do banco de dados na primeira execução.
    * Transações atômicas para garantir a integridade dos dados.

## Como Executar

1.  **Pré-requisitos:**
    * Python 3.x instalado.
    * Bibliotecas: `tkinter`, `customtkinter`, `textwrap`, `datetime`, `sqlite3`, `os` (geralmente inclusas na instalação padrão do Python, mas pode ser necessário instalar o `customtkinter` via pip).
2.  **Instalação das dependências (se necessário):**
    ```bash
    pip install customtkinter
    ```
3.  **Executar o script:**
    ```bash
    python main.py
    ```

## Estrutura do Código

O código é organizado em várias partes principais:

* **DatabaseManager:** Classe que gerencia a conexão e as operações com o banco de dados SQLite.
* **Classes do Modelo (Cliente, Conta, ContaCorrente):** Classes que representam as entidades do sistema bancário e encapsulam a lógica de negócios e a interação com o banco de dados.
* **LoginWindow:** Classe que implementa a tela de login.
* **BancoGUI:** Classe que implementa a interface gráfica principal da aplicação.
* **Execução Principal:** Bloco de código que inicializa o banco de dados e inicia a tela de login.

## Observações Importantes

* **Segurança:** **ATENÇÃO:** As senhas são armazenadas em texto plano no banco de dados, o que é extremamente inseguro para um ambiente de produção. Em um sistema real, deve-se usar técnicas de hash e salt para armazenar as senhas de forma segura.
* **Tratamento de Erros:** O código inclui tratamento de erros com `try-except` para lidar com exceções do banco de dados e outras situações inesperadas.  A interface gráfica também exibe mensagens de erro para o usuário.
* **Design:** A interface gráfica é construída com a biblioteca `customtkinter`, que fornece widgets modernos e temas visualmente atraentes.

## Melhorias Futuras

* Implementar a segurança adequada para o armazenamento de senhas (hashing com salt).
* Adicionar mais validações e tratamento de erros.
* Implementar funcionalidades adicionais, como relatórios, agendamento de pagamentos, etc.
* Melhorar o design da interface gráfica.
* Adicionar testes unitários.
