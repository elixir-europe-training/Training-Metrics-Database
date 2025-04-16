FROM nginx:alpine
ARG PAGE_NAME="disabled-site"
ARG PAGE_CONTENT=""

COPY ./app/static/vendor /usr/share/nginx/html/vendor
COPY ./app/static/img /usr/share/nginx/html/img
COPY "./app/static/pages/${PAGE_NAME}.html" /usr/share/nginx/html/index.html
COPY ./maintenance/nginx.conf /etc/nginx/conf.d/default.conf

RUN export PAGE_CONTENT=$(printf '%s\n' "$PAGE_CONTENT" | sed -e 's/[\/&]/\\&/g'); \
    sed -i "s/{{page_content}}/${PAGE_CONTENT}/g" /usr/share/nginx/html/index.html

