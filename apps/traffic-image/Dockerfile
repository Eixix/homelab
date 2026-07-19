FROM node:24-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY server.mjs ./server.mjs

ENV NODE_ENV=production
EXPOSE 3000
USER node
CMD ["node", "server.mjs"]
