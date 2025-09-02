# VLLM Proxy

A proxy for vLLM.


## Run for development

```bash
# Run production server
uvicorn main:app --host 0.0.0.0 --reload

# Run development server
fastapi dev main.py --host 0.0.0.0
```


## Production 

### Build for production

```bash
bash docker/build.sh
```

### Run for production

```bash
cd docker
docker compose up -d
```

## Tests

### Quick Start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r src/requirements.txt
pip install pytest pytest-asyncio respx
./run_tests.sh
```

For detailed testing documentation, see [TESTING.md](./TESTING.md).
