# GPU quote requires pynvml, which requires cuda, so use vllm image instead of python3
FROM vllm/vllm-openai:v0.9.1

# Install dependencies
WORKDIR /tmp

# Install packages via requirements.txt instead of poetry
# because of nv-ppcie-verifier requires some old version packages,
# which is not compatible with lots of current dependencies.
COPY src/requirements.txt ./
RUN pip install --no-cache-dir --upgrade -r requirements.txt \
    && rm -rf requirements.txt

# Copy source code
WORKDIR /app
COPY src ./
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
