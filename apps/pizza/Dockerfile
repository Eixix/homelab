FROM node:24-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY public ./public
COPY src ./src
COPY config/pizza-equivalences.json ./config/pizza-equivalences.json

ENV NODE_ENV=production
EXPOSE 3000
USER node
CMD ["node", "src/server.js"]
