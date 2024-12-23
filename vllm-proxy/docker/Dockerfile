FROM vllm/vllm-openai:v0.5.4 as base

WORKDIR /tmp

# openai patch
COPY docker/ ./docker/
RUN cd docker \
    && ./install_patch.sh \
    && cd .. \
    && rm -rf docker

# poetry
RUN pip install poetry
COPY ./pyproject.toml ./poetry.lock* ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes \
    && pip install --no-cache-dir --upgrade -r requirements.txt \
    && rm -rf requirements.txt

FROM base as runtime

WORKDIR /app

COPY src ./

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
