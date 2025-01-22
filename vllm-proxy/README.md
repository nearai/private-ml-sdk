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

```bash
cd src
python -m unittest tests
```