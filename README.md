
# Tripo-Backend

## Project Description

Tripo-Backend is a FastAPI-based backend service for the Tripo platform. It provides various functionalities such as user authentication, email verification, password reset, and user profile management.

## Features

- User Signup and Login
- Email Verification
- Password Reset
- User Profile Management
- CORS Middleware
- Database Integration with SQLAlchemy
- Environment Variable Management with dotenv

## Technologies Used

- **FastAPI**: A modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
- **SQLAlchemy**: The Python SQL toolkit and Object-Relational Mapping (ORM) library.
- **Uvicorn**: A lightning-fast ASGI server implementation, using `uvloop` and `httptools`.
- **dotenv**: A zero-dependency module that loads environment variables from a `.env` file.

## Setup Instructions

### Prerequisites

- Python 3.7+
- PostgreSQL database

### Installation

1. **Clone the repository:**

    ```sh
    git clone https://github.com/dabster108/Tripo--Backend.git
    cd Tripo--Backend
    ```

2. **Create and activate a virtual environment:**

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install the dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

4. **Set up the environment variables:**

    Create a `.env` file in the root directory and add the following variables:

    ```properties
    # Application settings
    SECRET_KEY=your-secret-key-here
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
    ENVIRONMENT=development

    # Database settings
    DATABASE_URL=postgresql://username:password@hostname:port/dbname
    ```

5. **Run the database migrations:**

    ```sh
    alembic upgrade head
    ```

6. **Start the application:**

    ```sh
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

## Usage

### API Endpoints

- **Signup:**
    - `POST /auth/signup/initial`
- **Verify Email:**
    - `POST /auth/verify-email`
- **Login:**
    - `POST /auth/login`
- **Get Current User Info:**
    - `GET /auth/me`
- **Resend Verification:**
    - `POST /auth/resend-verification`
- **Check Email:**
    - `POST /auth/check-email`
- **Forgot Password:**
    - `POST /auth/forgot-password`
- **Reset Password:**
    - `POST /auth/reset-password`

### Example Requests

#### Signup

```sh
curl -X POST "http://localhost:8000/auth/signup/initial" -H "accept: application/json" -H "Content-Type: application/json" -d '{"email": "user@example.com", "password": "string"}'
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contact

For any inquiries, please contact Dikshanta.

tripo-backend/
  └── app/
      ├── __init__.py          → Package initializer
      ├── main.py              → Entry point of the application
      ├── config.py            → Configuration settings
      ├── database.py          → Database connection and setup
      │
      ├── models/              → Database models
      │   ├── __init__.py      → Package initializer for models
      │   └── user.py          → User model definition
      │
      ├── schemas/             → Pydantic schemas for data validation
      │   ├── __init__.py      → Package initializer for schemas
      │   └── user.py          → User schema definition
      │
      ├── routers/             → API route definitions
      │   ├── __init__.py      → Package initializer for routers
      │   └── auth.py          → Authentication routes
      │
      ├── core/                → Core functionalities
      │   ├── __init__.py      → Package initializer for core
      │   ├── security.py      → Security utilities (e.g., token handling)
      │   └── exceptions.py    → Custom exceptions
      │
      └── utils/               → Utility functions
          ├── __init__.py      → Package initializer for utils
          └── validators.py    → Input validators
