FROM node:26-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
COPY scripts ./scripts
RUN npm ci

FROM node:26-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ARG NEXT_PUBLIC_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty
ARG NEXT_PUBLIC_MAP_SATELLITE_STYLE_URL=
ARG NEXT_PUBLIC_MAP_TERRAIN_STYLE_URL=
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_MAP_STYLE_URL=$NEXT_PUBLIC_MAP_STYLE_URL
ENV NEXT_PUBLIC_MAP_SATELLITE_STYLE_URL=$NEXT_PUBLIC_MAP_SATELLITE_STYLE_URL
ENV NEXT_PUBLIC_MAP_TERRAIN_STYLE_URL=$NEXT_PUBLIC_MAP_TERRAIN_STYLE_URL
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN npm run postinstall && npm run build

FROM node:26-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000
RUN addgroup -S -g 10001 streetguard \
    && adduser -S -u 10001 -G streetguard streetguard
COPY --from=builder --chown=10001:10001 /app/.next/standalone ./
COPY --from=builder --chown=10001:10001 /app/.next/static ./.next/static
COPY --from=builder --chown=10001:10001 /app/public ./public
USER 10001:10001
EXPOSE 3000
CMD ["node", "server.js"]
