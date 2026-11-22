FROM nginxinc/nginx-unprivileged:stable-alpine
COPY index.html mapa.html LICENSE README.md GUIA.md ARQUITECTURA.md /usr/share/nginx/html/
COPY datos /usr/share/nginx/html/datos
COPY docs /usr/share/nginx/html/docs
COPY casos /usr/share/nginx/html/casos
COPY communications /usr/share/nginx/html/communications
