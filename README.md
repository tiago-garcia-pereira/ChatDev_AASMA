# AASMA / ChatDev Project Setup

This document describes the procedure required to configure the project after cloning the repository, and to execute both the complete application and the autonomous debugger through its command line interface.

This project is a fork of the ChatDev framework. The work developed in this fork is primarily located in the `debugger_agents` directory and in the `yaml_instance/autonomous_code_debugger.yaml` workflow.

## 1. Requirements

The following software must be installed in advance:

- Python 3.12
- Node.js 18 or later
- `npm`
- `make`
- `uv`
- Ollama
- Ollama model `qwen2.5-coder:3b`

If `uv` is not already installed, it may be installed as follows:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ollama should be installed from:

```text
https://ollama.com/download
```

After installing Ollama, download the model used by the autonomous debugger:

```bash
ollama pull qwen2.5-coder:3b
```

Verify the installed versions:

```bash
python3 --version
node --version
npm --version
uv --version
make --version
ollama --version
```

All commands presented below assume that they are executed from within the `ChatDev_AASMA` directory.

## 2. Environment Configuration

Create a local `.env` file:

```bash
cp .env.example .env
```

After copying `.env.example`, the environment variables are configured to use Ollama locally. The expected configuration is:

```env
BASE_URL=http://localhost:11434/v1
API_KEY=ollama
```

The `yaml_instance/autonomous_code_debugger.yaml` workflow uses these variables to invoke the model configured for the agents.

## 3. Dependency Installation

### Python Backend

The recommended installation method uses `uv`:

```bash
uv sync
```

This command creates or updates the project `.venv` environment with the dependencies specified in `pyproject.toml`.


The `requirements.txt` file also includes `ruff` and `mypy`, which are used by the autonomous debugger static analyzer when available.

### Frontend

```bash
cd frontend
npm install
cd ..
```

The root-level `package.json` includes the `kill-port` dependency used by the `make stop` target. To install this optional dependency, run the following command from the `ChatDev_AASMA` directory:

```bash
npm install
```

## 4. Running the Complete Application

To start the backend and frontend simultaneously, run:

```bash
make dev
```

This command starts:

- the backend at `http://localhost:6400`
- the frontend at `http://localhost:5173`

Open the application in a browser:

```text
http://localhost:5173
```

To stop the servers, run:

```bash
make stop
```

## 5. Running the Autonomous Debugger Through the ChatDev Interface

After starting the application with `make dev`, access the web interface:

```text
http://localhost:5173
```

To launch the autonomous debugger through the interface:

1. Click `Workflows`.
2. Select the `autonomous_code_debugger.yaml` YAML file.
3. Click `Launch`.
4. Provide the path to the project or file to be analyzed, for example:

```text
PROJECT_PATH: /path/to/file_or_project
```

After launch, the workflow executes the nodes defined in the YAML file, including `Input Context`, `Auto Reproducer`, `Static Analyzer`, the fixer agents, the judge agents, and the final consensus stage.

## 7. Running the Autonomous Debugger Command Line Interface

The main command is:

```bash
make debug PROJECT_PATH=/path/to/file.py
```



## 8. Troubleshooting Notes

If `make dev` fails because a port is already in use, stop any previous processes:

```bash
make stop
```

If the `.venv` environment does not exist, run:

```bash
uv sync
```

If the frontend dependencies are missing, run:

```bash
cd frontend
npm install
```

If the autonomous debugger is unable to invoke the models, verify that `API_KEY` and `BASE_URL` are defined in the `.env` file.
