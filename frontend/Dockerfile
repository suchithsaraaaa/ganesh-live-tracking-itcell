FROM node:22-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . ./
RUN npm run build

FROM alpine:latest
WORKDIR /dist
COPY --from=build /app/dist /dist
CMD ["sh", "-c", "cp -r /dist/* /target/"]
