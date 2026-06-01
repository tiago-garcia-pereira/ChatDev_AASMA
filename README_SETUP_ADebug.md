# Configuração do Projeto AASMA / ChatDev

Este guia descreve como preparar o projeto após o `git clone` e como executar tanto a aplicação completa como o autonomous debugger em command line interface.

## 1. Requisitos

Instale previamente:

- Python 3.12
- Node.js 18 ou superior
- `npm`
- `make`
- `uv`
- Ollama
- modelo Ollama `qwen2.5-coder:3b`

Para instalar o `uv`, caso ainda não esteja disponível:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Instale o Ollama a partir de:

```text
https://ollama.com/download
```

Após instalar o Ollama, descarregue o modelo utilizado pelo autonomous debugger:

```bash
ollama pull qwen2.5-coder:3b
```

Confirme as versões:

```bash
python3 --version
node --version
npm --version
uv --version
make --version
ollama --version
```

Todos os comandos abaixo assumem que a execução ocorre dentro da pasta `ChatDev_AASMA`.

## 2. Configurar variáveis de ambiente

Crie o ficheiro local `.env`:

```bash
cp .env.example .env
```

Ao copiar o `.env.example`, as variáveis ficam definidas para utilizar localmente o Ollama. A configuração esperada é:

```env
BASE_URL=http://localhost:11434/v1
API_KEY=ollama
```

O workflow `yaml_instance/autonomous_code_debugger.yaml` utiliza estas variáveis para chamar o modelo configurado nos agentes.

## 3. Instalar dependências

### Backend Python

Forma recomendada, utilizando `uv`:

```bash
uv sync
```

Este comando cria ou atualiza a `.venv` do projeto com as dependências do `pyproject.toml`.

Alternativa com `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

O `requirements.txt` inclui também `ruff` e `mypy`, utilizados pelo static analyzer do autonomous debugger quando estiverem disponíveis.

### Frontend

```bash
cd frontend
npm install
cd ..
```

Opcional, mas útil para o comando `make stop`:

```bash
npm install
```

## 4. Executar a aplicação completa

Para iniciar backend e frontend em conjunto:

```bash
make dev
```

Este comando inicia:

- backend em `http://localhost:6400`
- frontend em `http://localhost:5173`

Abra no browser:

```text
http://localhost:5173
```

Para parar os servidores:

```bash
make stop
```

## 5. Executar manualmente, sem Makefile

Backend:

```bash
uv run python server_main.py --port 6400 --reload
```

Frontend:

```bash
cd frontend
VITE_API_BASE_URL=http://localhost:6400 npm run dev
```

Em Windows PowerShell, utilize:

```powershell
cd frontend
$env:VITE_API_BASE_URL="http://localhost:6400"
npm run dev
```

## 6. Executar o autonomous debugger Command Line Interface

O comando principal é:

```bash
make debug PROJECT_PATH=/caminho/para/ficheiro_ou_projeto
```

Exemplo com um ficheiro Python:

```bash
make debug PROJECT_PATH=/home/user/projeto/erros_qwen/erro1.py
```

O debugger tenta inferir automaticamente o comando de teste:

- ficheiro `.py`: `python3 ficheiro.py`
- diretório com `tests/` ou `pytest.ini`: `python3 -m pytest`
- diretório com `main.py`: `python3 main.py`
- outro caso: `python3 -m compileall -q .`

Também é possível passar o caminho no formato alternativo suportado pelo Makefile:

```bash
make debug PROJECT_PATH:/caminho/para/ficheiro_ou_projeto
```

## 7. Executar o autonomous debugger Command Line Interface manualmente

O `make debug` chama internamente:

```bash
.venv/bin/python -m debugger_agents.cli "/caminho/para/ficheiro_ou_projeto"
```

Caso a venv esteja ativa, também é possível utilizar:

```bash
python -m debugger_agents.cli "/caminho/para/ficheiro_ou_projeto"
```

## 8. Comandos úteis

Ver os comandos disponíveis:

```bash
make help
```

Validar YAMLs:

```bash
make validate-yamls
```

Sincronizar Vue graphs:

```bash
make sync
```

Executar testes backend:

```bash
make backend-tests
```

Executar lint backend:

```bash
make backend-lint
```

Executar testes e lint:

```bash
make check-backend
```

## 9. Notas de troubleshooting

Se `make dev` falhar porque uma porta já está ocupada, pare processos antigos:

```bash
make stop
```

Se a `.venv` não existir, execute:

```bash
uv sync
```

Se o frontend não encontrar dependências:

```bash
cd frontend
npm install
```

Se o autonomous debugger não conseguir chamar os modelos, confirme se o `.env` tem `API_KEY` e `BASE_URL` preenchidos.
