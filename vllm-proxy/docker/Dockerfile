# GPU quote requires pynvml, which requires cuda, so use vllm image instead of python3
FROM vllm/vllm-openai:v0.9.1

# Install dependencies
WORKDIR /tmp
COPY src/requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt \
    && rm -rf requirements.txt

# Copy source code
WORKDIR /app
COPY src ./
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
