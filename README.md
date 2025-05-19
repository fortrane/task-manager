# Task Manager API

![Task Manager API](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.103.0%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 📝 Project Overview

The Task Manager API is a comprehensive task management solution designed to help individuals and teams organize, track, and complete their tasks efficiently. Built with modern technologies and best practices, this system provides a robust backend for task management applications.

This API allows users to:
- Create and manage tasks with rich metadata (priorities, categories, statuses)
- Track time spent on tasks with detailed reporting
- Set up recurring tasks for routine activities
- Receive timely reminders about upcoming deadlines
- Access and manage tasks via Telegram bot integration
- Monitor system performance with extensive metrics

The project follows a microservices architecture using Docker containers, with a FastAPI backend, PostgreSQL database, and various supporting services for monitoring and notification delivery. It's designed to be scalable, maintainable, and easy to deploy in any environment.

Whether you're building a personal task manager, a team collaboration tool, or integrating task management into a larger system, this API provides all the necessary backend functionality with a clean, documented interface.

## 📋 Features

- **User Authentication** - Secure JWT-based authentication system
- **Task Management** - Create, read, update, delete tasks with various attributes:
  - Task priorities (low, medium, high, urgent)
  - Task statuses (todo, in progress, done, canceled)
  - Task categories (personal, work, health, education, other)
  - Due dates and descriptions
- **Time Tracking** - Track time spent on tasks
- **Recurring Tasks** - Set up tasks that repeat on a schedule
- **Reminders System** - Get notified about upcoming tasks
- **Telegram Integration** - Receive notifications and manage tasks via Telegram
- **Comprehensive Metrics** - Monitor application performance with Prometheus and Grafana
- **API Documentation** - Interactive API docs powered by Swagger/OpenAPI
- **Containerized Deployment** - Easily deploy with Docker and Docker Compose
- **CI/CD Pipeline** - Integration with Jenkins for continuous deployment

## 🛠️ Tech Stack

- **Backend**:
  - [FastAPI](https://fastapi.tiangolo.com/) - High-performance API framework
  - [SQLAlchemy](https://www.sqlalchemy.org/) - SQL Toolkit and ORM
  - [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation and settings management
  - [Python-Jose](https://github.com/mpdavis/python-jose) - JWT token handling
  - [Passlib](https://passlib.readthedocs.io/en/stable/) - Password hashing

- **Database**:
  - [PostgreSQL](https://www.postgresql.org/) - Robust relational database

- **Messaging**:
  - [aiogram](https://github.com/aiogram/aiogram) - Asynchronous framework for Telegram Bot API

- **Monitoring**:
  - [Prometheus](https://prometheus.io/) - Metrics collection and alerting
  - [Grafana](https://grafana.com/) - Metrics visualization and dashboards

- **DevOps**:
  - [Docker](https://www.docker.com/) - Containerization
  - [Docker Compose](https://docs.docker.com/compose/) - Multi-container orchestration
  - [Traefik](https://traefik.io/) - Modern HTTP reverse proxy
  - [Jenkins](https://jenkins.io/) - Automation server for CI/CD

- **Testing**:
  - [Pytest](https://pytest.org/) - Testing framework
  - [Locust](https://locust.io/) - Load testing

## 🏗️ Architecture

The application follows a clean architecture with separation of concerns:

- **Models**: Database models using SQLAlchemy ORM
- **Schemas**: Data validation and serialization with Pydantic
- **API Endpoints**: Organized in a modular way with FastAPI routers
- **Core**: Configuration, database setup, and security
- **Utilities**: Helper functions and metrics reporting

## 🚀 Installation & Setup

### Prerequisites

- Docker and Docker Compose

### Docker Deployment

1. Clone the repository:
   ```bash
   git clone https://github.com/fortrane/task-manager.git
   cd task-manager
   ```

2. Customize the `.env` file with your configuration:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

3. Start the stack with Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Access the services:
   - API direct access: http://localhost:8000
   - API through Traefik: http://api.localhost
   - API Documentation: http://api.localhost/docs
   - Traefik Dashboard: http://localhost:8080
   - Prometheus through Traefik: http://prometheus.localhost
   - Grafana through Traefik: http://grafana.localhost (default credentials: admin/admin)
   - Jenkins through Traefik: http://jenkins.localhost

## 🔀 Traefik Routing

The application uses Traefik as a reverse proxy and load balancer. Here's how the routing is configured:

| Service | URL | Description |
|---------|-----|-------------|
| API | http://api.localhost | Main API application |
| Prometheus | http://prometheus.localhost | Metrics collection |
| Grafana | http://grafana.localhost | Metrics visualization |
| Jenkins | http://jenkins.localhost | CI/CD automation |
| Traefik Dashboard | http://localhost:8080 | Traefik's own dashboard |

Traefik automatically discovers services through Docker labels and routes traffic accordingly. The configuration includes:

- Automatic HTTP routing based on host names
- Metrics collection for Prometheus
- Dashboard access for monitoring

Example configuration from docker-compose.yml:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.api.rule=Host(`api.localhost`)"
  - "traefik.http.services.api.loadbalancer.server.port=8000"
```

## 📊 Monitoring & Metrics

This project comes with a comprehensive monitoring solution:

- **Application Metrics**:
  - Request counts, latency, and error rates
  - Task creation and completion metrics
  - Telegram notification metrics

- **Grafana Dashboards**:
  - Task Management Dashboard - Overview of task metrics
  - API Performance Dashboard - API request metrics
  - System Dashboard - Host and container metrics

## 📱 Telegram Bot Features

The integrated Telegram bot provides the following commands:

- `/start` - Start the bot
- `/help` - Show available commands
- `/tasks` - Show all your tasks
- `/today` - Show tasks due today
- `/week` - Show tasks due this week
- `/status` - Show tasks by status
- `/priority` - Show tasks by priority
- `/category` - Show tasks by category

## 🔄 CI/CD Pipeline

The project includes a Jenkinsfile that provides a simple CI/CD pipeline example:

1. **Checkout**: Clone the repository
2. **Setup**: Install dependencies
3. **Lint**: Run code quality checks
4. **Test**: Run test suite with pytest
5. **Build**: Build Docker images
6. **Deploy**: Deploy to the environment

**Note**: This CI/CD configuration is provided as a demonstration example and is not optimized for production use. For production deployments, you would need to customize the pipeline with proper security controls, environment-specific configurations, and more comprehensive testing strategies.

## 🧪 Testing

Run tests inside the Docker containers:

### Unit Tests

Execute the test suite with pytest:

```bash
docker-compose exec api pytest tests/test_api.py -v
```

### Load Testing

Run load tests with Locust:

```bash
# Low load test
docker-compose exec api locust -f tests/locustfile.py --host=http://api:8000 --headless -u 5 -r 1 --run-time 1m

# Medium load test
docker-compose exec api locust -f tests/locustfile.py --host=http://api:8000 --headless -u 10 -r 2 --run-time 2m

# High load test
docker-compose exec api locust -f tests/locustfile.py --host=http://api:8000 --headless -u 20 -r 3 --run-time 3m
```

Then access the Locust web interface at http://localhost:8089.

## 📚 API Documentation

After starting the application, you can access the interactive API documentation:

- Swagger UI: http://api.localhost/docs
- ReDoc: http://api.localhost/redoc

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

Built with ❤️
