ARG NODE_BASE_IMAGE=node:22-alpine
FROM ${NODE_BASE_IMAGE} AS build
WORKDIR /app
COPY package.json ./
RUN yarn install --non-interactive --no-lockfile
COPY . .
ENV REACT_APP_BACKEND_URL=""
ENV CI=false
RUN yarn build
ARG NGINX_BASE_IMAGE=nginx:1.27-alpine
FROM ${NGINX_BASE_IMAGE}
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
