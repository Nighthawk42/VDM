# VDM Project To-Do List

This document tracks major functional, operational, and architectural improvements for the VDM server. Unlike `roadmap.md`, this list is focused on engineering and deployment tasks rather than user-facing gameplay features.

---
## 1. Production-Ready Web Server & SSL

**Goal:** Move beyond the development server and `mkcert` to a proper, secure production setup.

- **[ ] Reverse Proxy:** Deploy the application behind a production-grade reverse proxy like **Nginx** or **Caddy**. This is the standard for web applications, providing better performance, security, and stability than running Uvicorn directly exposed to the internet.
- **[ ] Proper SSL:** Use the reverse proxy to manage SSL certificates automatically with **Let's Encrypt**. This will provide a real, trusted certificate for any domain the application is hosted on, removing the need for `mkcert`.
- **[ ] Process Management:** Use a process manager like **Gunicorn** to run the FastAPI application, allowing for multiple worker processes and better resource management.

---
## 2. Docker Support

**Goal:** Containerize the entire application for easy, reproducible, and isolated deployments.

- **[ ] Create a `Dockerfile`:** Define the environment for the VDM server, including the Python version, dependency installation from `requirements.txt`, and the command to run the server.
- **[ ] Create a `docker-compose.yml`:** Write a Compose file to make it trivial to start the entire application stack (the VDM server and potentially its databases) with a single `docker-compose up` command. This dramatically simplifies setup for new developers and production environments.
