# CodeMark
*"Make grading assignments as easy as ABC!"*

## Things You Need
- [Docker](https://docs.docker.com/get-docker/)

- [Docker Compose](https://docs.docker.com/compose/install/)

## Running The App
1. Clone the repo and `cd` into the repo

2. Use `.json.config.example` to create a `json.config` file under the `/project` directory with your credentials such as:
    ```
    {
      "SECRET_KEY": "DFJKdslkjfo23jrfadsjka20jr",
      "DEBUG": "True",
      "EMAIL_HOST": "smtp.FAKE_SMTP_HOST.com",
      "EMAIL_PORT": "587",
      "EMAIL_HOST_USER": "FAKE_SMTP_USER",
      "EMAIL_HOST_PASSWORD": "FAKE_SMTP_PASSWORD",
      "EMAIL_USE_TLS": "True",
      "DEFAULT_FROM_EMAIL": "FAKE_SMTP_USER@FAKE_SMTP_HOST.com"
    }
    ```

    - **SECRET_KEY** is a shared secret used by Django for encrypting and decrypting information
    - **DEBUG** is a  Django environment variable that enables certain debug features

4. Commands:
   - `docker-compose run web /bin/bash` will start a Bash shell inside a Docker container.
      - Inside the `/project` directory `python manage.py makemigrations codemark` will make necessary Django model changes for the app.
      - Inside the `/project` directory `python manage.py migrate` will create the Django database.
   - `docker-compose up --build` will launch the website at the URL [localhost:8000](localhost:8000)