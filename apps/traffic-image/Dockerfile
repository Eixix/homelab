FROM node:24-alpine

WORKDIR /app
COPY server.mjs ./server.mjs

ENV NODE_ENV=production
EXPOSE 3000
USER node
CMD ["node", "server.mjs"]
