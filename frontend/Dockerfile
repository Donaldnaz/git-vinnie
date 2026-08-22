FROM nginx:1.27-alpine

# Copy the single page app
COPY index.html /usr/share/nginx/html/index.html

# Copy the config template. It uses ${TICKET_API_URL} and ${NOTIFICATION_SERVICE_URL}
# which are substituted at container startup by the entrypoint below.
COPY nginx.conf /etc/nginx/templates/default.conf.template

# nginx:alpine includes envsubst. The official image automatically processes
# any *.template files in /etc/nginx/templates/ and writes the result to
# /etc/nginx/conf.d/ before Nginx starts. No custom entrypoint needed.
