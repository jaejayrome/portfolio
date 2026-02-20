FROM python:3.12-slim AS pdf-builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  texlive-latex-base \
  texlive-fonts-recommended \
  texlive-fonts-extra \
  texlive-latex-extra \
  && rm -rf /var/lib/apt/lists/*

COPY data/ ./data/
COPY pdf/ ./pdf/

RUN pip install beautifulsoup4 pyyaml jinja2

RUN cd pdf && python build.py

FROM python:3.12-slim AS web-builder
WORKDIR /app

COPY data/ ./data/
COPY web/ ./web/

RUN pip install pyyaml jinja2 markdown

RUN cd web && python build.py

FROM nginx:alpine AS final

COPY nginx/nginx.conf /etc/nginx/nginx.conf 

COPY --from=web-builder /app/web/output /app/web/output

COPY --from=pdf-builder /app/pdf/output /app/pdf/output

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
