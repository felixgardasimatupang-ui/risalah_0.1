---
name: ask-docker-best-practices
description: Best practices for Docker images, Dockerfiles, and containerized deployments. Focuses on image size, security, and maintainability.
---

---
name: ask-docker-best-practices
description: Docker best practices for image optimization, security hardening, and maintainable Dockerfiles.
triggers: ["docker best practices", "optimize docker image", "dockerfile tips", "secure container", "reduce image size"]
---

<critical_constraints>
❌ NO privileged containers unless proven necessary
❌ NO hardcoded secrets or env vars in Dockerfile
❌ NO running as root
❌ NO using latest tag on base images
✅ MUST pin base image versions (e.g. node:18-alpine3.18)
✅ MUST use .dockerignore
✅ MUST use multi-stage builds for compiled apps
✅ MUST use COPY over ADD unless ADD features needed
</critical_constraints>

<dockerfile_structure>
1. Base image (pinned)
2. Set WORKDIR
3. Copy dependency manifests (package.json, requirements.txt)
4. Install dependencies
5. Copy source code
6. Build (if needed)
7. Set runtime user
8. Define CMD/ENTRYPOINT
</dockerfile_structure>

<image_optimization>
- Use alpine or slim variants
- Combine RUN statements to reduce layers
- Use --no-cache for apk add
- Clean up temp files in same RUN layer
- Use .dockerignore: node_modules, .git, .env, dist (if build stage used)
- Remove build tooling in final stage
</image_optimization>

<security>
- Use USER directive (non-root)
- Scan with docker scan or trivy
- Avoid ADD for remote URLs (use curl/wget instead)
- Set read-only root filesystem: --read-only
- Use secrets mounts (BuildKit): --mount=type=secret
- Capability drop: --cap-drop=ALL --cap-add=NEEDED_ONLY
</security>

<compose_best_practices>
- Use healthcheck for service dependencies
- Set restart policies (unless-stopped)
- Use named volumes for persistent data
- Use .env file for secrets
- Avoid depends_on without healthcheck
- Set resource limits (memory, cpus)
</compose_best_practices>

<heuristics>
- Large image → check base image, multi-stage, cached layers
- Permission errors → missing USER or chown
- Build cache miss → reorder layers, check .dockerignore
- Container exits immediately → check CMD syntax, logs
</heuristics>
