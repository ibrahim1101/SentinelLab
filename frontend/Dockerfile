FROM node:22-alpine AS build
WORKDIR /app
COPY package.json ./
RUN yarn install --non-interactive --no-lockfile
COPY . .
ENV REACT_APP_BACKEND_URL=""
ENV CI=false
RUN yarn build
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
