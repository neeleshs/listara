# Todo List App with Nanodjango and HTMX

A simple, single-file todo list application built with nanodjango and HTMX.

## Features

- **Create multiple todo lists** with unique IDs
- **Add, edit, and remove items** from each list
- **Local storage tracking** - visited lists are stored in browser localStorage
- **HTMX interactions** for smooth, no-refresh updates
- **SQLite database** for persistent storage
- **Single-file Django app** using nanodjango

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
nanodjango run app.py
```

Or directly with Python:
```bash
python app.py
```

3. Open your browser to `http://localhost:8000`

## How it Works

- **Home Page**: Shows all your todo lists and lets you create new ones
- **List Page**: Click on any list to view and manage its items
- **Local Storage**: When you visit a list, it's stored in your browser's localStorage
- **HTMX**: All interactions (add, edit, delete) happen without page refreshes

## Database

The app uses SQLite by default (stored as `db.sqlite3`). The database is created automatically on first run.

## Models

- **TodoList**: Stores list name with UUID as primary key
- **TodoItem**: Single line text items linked to a TodoList

## Converting to Full Django Project

If you want to convert this to a full Django project structure:

```bash
nanodjango convert app.py myproject
```

This will create a standard Django project with proper app structure.