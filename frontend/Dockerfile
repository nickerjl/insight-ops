# InsightOps frontend image.
#
#  - `development` target: Vite dev server on :5173 with HMR + /api proxy
#    (used by docker compose locally — matches README http://localhost:5173).
#  - `production` target: built static assets served by nginx (used when the
#    app is run as a container instead of S3+CloudFront).
#
# The production deployment path builds `dist/` and uploads it to S3; nginx
# here is only a convenience for container-based demos.
FROM node:18.20.4-alpine AS build
WORKDIR /app
COPY package*.json ./
# npm install (not ci) so the image builds without a committed lockfile;
# commit package-lock.json after the first build for reproducible builds.
RUN npm install
COPY . .
RUN npm run build

FROM node:18.20.4-alpine AS development
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# node images ship an unprivileged `node` user.
USER node
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM nginx:1.27.2-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
