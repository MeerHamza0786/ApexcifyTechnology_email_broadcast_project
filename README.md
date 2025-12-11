## Broadcast Studio Web

A hybrid bulk-email workspace composed of the original async mailer package (`app/`) and a modern Flask front end (`webapp/`). Use the GUI to manage recipients, compose drafts, and prepare broadcasts before handing off to the existing SMTP engine.

### Structure
```
email_broadcast_project/
├── app/                # original Python package (config, mailer, logging)
├── storage/logs/       # rolling broadcast logs
├── webapp/             # Flask UI (templates + static assets)
├── main.py             # optional launcher (imports app + web)
├── requirements.txt    # shared dependencies
└── .env                # secrets + runtime config
```

### Getting Started
1. **Python**: Install Python 3.10+ and create/activate a virtual environment.
2. **Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment**: Set values in `.env` (admin credentials, concurrency defaults, etc.).
4. **Run the Web UI**:
   ```bash
   python main.py
   # or: flask --app webapp.app run --debug
   ```
5. **Login**: Visit `http://localhost:5000`, sign in with the credentials defined in `.env`, review recipients, and compose a mailing.

### Notes
- The legacy async mailer remains in `app/services/mailer.py`; wiring the Flask UI to fire real sends can be done later by invoking those services from `webapp/app.py`.
- Logs continue to write to `storage/logs/broadcast.log`.
- Customize styling via `webapp/static/style.css` and HTML templates under `webapp/templates/`.

# ApexcifyTechnology_email_broadcast_project
