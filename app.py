#!/usr/bin/env python
"""
A simple todo list app using nanodjango and HTMX
Run with: nanodjango run app.py
Or directly: python app.py
"""
from nanodjango import Django
from django.db import models
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
import uuid

# Create the Django app
import os
import dj_database_url

# Database configuration - auto-detect Railway PostgreSQL or use SQLite
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Get production domain from environment or use wildcard for Railway
IS_PRODUCTION = bool(os.environ.get("RAILWAY_PUBLIC_DOMAIN", ""))

# Build CSRF trusted origins list
CSRF_ORIGINS = []
if IS_PRODUCTION:
    # Add common Railway domains
    CSRF_ORIGINS = [
        "https://*.up.railway.app",
        "https://*.railway.app",
    ]
    # Add specific domain if provided
    if os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
        CSRF_ORIGINS.append(f"https://{os.environ.get('RAILWAY_PUBLIC_DOMAIN')}")

app = Django(
    ALLOWED_HOSTS=["*"],
    SECRET_KEY=os.environ.get("SECRET_KEY", "your-secret-key-change-in-production"),
    CSRF_USE_SESSIONS=False,  # Use cookies for CSRF tokens
    CSRF_COOKIE_HTTPONLY=False,  # Allow JavaScript to read the CSRF cookie
    CSRF_COOKIE_SECURE=IS_PRODUCTION,  # Use secure cookies in production
    CSRF_TRUSTED_ORIGINS=CSRF_ORIGINS,
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    DEBUG=os.environ.get("DEBUG", "False") == "True",
    DATABASES=DATABASES,
)

# Models
@app.admin
class TodoList(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/list/{self.id}/'


@app.admin
class TodoItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    todo_list = models.ForeignKey(TodoList, on_delete=models.CASCADE, related_name='items')
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return self.text


# Base template
BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Todo Lists{% endblock %}</title>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 0;
            margin: 0;
        }

        /* Mobile container */
        .mobile-container {
            max-width: 430px;
            margin: 0 auto;
            background: #f8f9fa;
            min-height: 100vh;
            position: relative;
            box-shadow: 0 0 40px rgba(0,0,0,0.2);
        }

        /* App header */
        .app-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }

        .app-header h1 {
            font-size: 22px;
            font-weight: 600;
            margin: 0;
        }

        .app-header p {
            opacity: 0.9;
            font-size: 13px;
            margin-top: 2px;
        }

        /* Header with back button */
        .header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Back button */
        .back-button {
            display: inline-flex;
            align-items: center;
            color: white;
            text-decoration: none;
            font-size: 14px;
            opacity: 0.9;
        }

        .back-button:hover {
            opacity: 1;
        }

        /* Main content */
        .content {
            padding: 15px;
        }

        /* Cards */
        .card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }

        .card h2 {
            font-size: 18px;
            color: #333;
            margin-bottom: 15px;
            font-weight: 600;
        }

        /* Form inputs */
        input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e9ecef;
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: #f8f9fa;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            background: white;
        }

        /* Primary button */
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            margin-top: 10px;
        }

        .btn-primary:active {
            transform: scale(0.98);
        }

        /* List items */
        .list-item {
            background: white;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        .list-item:active {
            transform: scale(0.98);
            background: #f8f9fa;
        }

        .list-item a {
            color: #333;
            text-decoration: none;
            font-size: 17px;
            font-weight: 500;
            flex: 1;
        }

        .list-item .list-meta {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
        }

        .list-item .date {
            color: #999;
            font-size: 12px;
        }

        /* Todo items */
        .todo-item {
            background: white;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            transition: all 0.2s ease;
        }

        .todo-item:active {
            transform: scale(0.98);
        }

        .todo-item-text {
            flex: 1;
            color: #333;
            font-size: 16px;
            padding-right: 10px;
        }

        /* Action buttons */
        .actions {
            display: flex;
            gap: 8px;
        }

        .btn-icon {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .btn-edit {
            background: #f0f2f5;
            color: #667eea;
        }

        .btn-edit:active {
            background: #667eea;
            color: white;
            transform: scale(0.9);
        }

        .btn-delete {
            background: #fee;
            color: #dc3545;
        }

        .btn-delete:active {
            background: #dc3545;
            color: white;
            transform: scale(0.9);
        }

        .btn-remove {
            background: #fee;
            color: #dc3545;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .btn-remove:active {
            background: #dc3545;
            color: white;
            transform: scale(0.95);
        }

        /* Edit form */
        .edit-form {
            display: flex;
            gap: 10px;
            flex: 1;
        }

        .edit-form input {
            flex: 1;
            padding: 10px;
        }

        .edit-form button {
            padding: 8px 16px;
            border-radius: 8px;
            border: none;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }

        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }

        .empty-state p {
            font-size: 16px;
            margin-bottom: 10px;
        }

        /* Floating action button */
        .fab {
            position: fixed;
            bottom: 25px;
            right: 25px;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
            z-index: 1000;
        }

        .fab:active {
            transform: scale(0.9);
        }

        /* Input group */
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }

        .input-group input {
            flex: 1;
        }

        /* Responsive adjustments */
        @media (max-width: 430px) {
            .mobile-container {
                max-width: 100%;
                box-shadow: none;
            }
        }

        /* Remove default button styles */
        button {
            -webkit-appearance: none;
            -moz-appearance: none;
            appearance: none;
        }

        /* Smooth scrolling */
        html {
            scroll-behavior: smooth;
        }
    </style>
    <script>
        // Store visited lists in localStorage
        function storeListVisit(listId, listName) {
            let visitedLists = JSON.parse(localStorage.getItem('visitedLists') || '{}');
            visitedLists[listId] = {
                name: listName,
                lastVisited: new Date().toISOString()
            };
            localStorage.setItem('visitedLists', JSON.stringify(visitedLists));
        }

        // Load visited lists on home page
        document.addEventListener('DOMContentLoaded', function() {
            if (window.location.pathname === '/') {
                // This will be populated with visited lists from localStorage
                let visitedLists = JSON.parse(localStorage.getItem('visitedLists') || '{}');
                console.log('Visited lists:', visitedLists);
            }
        });

        // Configure HTMX to include CSRF token
        document.addEventListener('DOMContentLoaded', function() {
            document.body.addEventListener('htmx:configRequest', function(event) {
                // Get CSRF token from cookie
                let csrfToken = getCookie('csrftoken');
                if (!csrfToken) {
                    // If not in cookie, try to get from meta tag or form
                    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
                    if (csrfInput) {
                        csrfToken = csrfInput.value;
                    }
                }
                if (csrfToken) {
                    event.detail.headers['X-CSRFToken'] = csrfToken;
                }
            });
        });

        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    </script>
</head>
<body>
    <div class="mobile-container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>"""


# Home page template
HOME_TEMPLATE = """{% extends "base.html" %}
{% block title %}Todo Lists - Home{% endblock %}
{% block content %}
<div class="app-header">
    <h1>My Todo Lists</h1>
</div>

<div class="content">
    <div class="card">
        <form id="create-list-form">
            {% csrf_token %}
            <input type="text" name="name" id="list-name" placeholder="Enter list name..." required>
            <button type="submit" class="btn-primary">Create New List</button>
        </form>
    </div>

    <div class="card">
        <h2>My Lists</h2>
        <div id="lists">
            <div class="empty-state">
                <p>Loading lists...</p>
            </div>
        </div>
    </div>
</div>

<script>
    // Function to generate UUID
    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Function to render lists from localStorage
    function renderLists() {
        const listsContainer = document.getElementById('lists');
        const storedLists = JSON.parse(localStorage.getItem('todoLists') || '{}');

        if (Object.keys(storedLists).length === 0) {
            listsContainer.innerHTML = '<div class="empty-state"><p>No lists yet. Create your first list above!</p></div>';
            return;
        }

        // Sort by creation date (most recent first)
        const sortedLists = Object.entries(storedLists).sort((a, b) => {
            return new Date(b[1].created) - new Date(a[1].created);
        });

        listsContainer.innerHTML = sortedLists.map(([id, list]) => {
            return `
                <div class="list-item">
                    <a href="/list/${id}/" onclick="storeListVisit('${id}', '${list.name}')">
                        ${list.name}
                    </a>
                    <button class="btn-remove" onclick="event.preventDefault(); deleteList('${id}')">
                        Remove
                    </button>
                </div>
            `;
        }).join('');
    }

    // Handle form submission
    document.getElementById('create-list-form').addEventListener('submit', async function(e) {
        e.preventDefault();

        const nameInput = document.getElementById('list-name');
        const name = nameInput.value.trim();

        if (!name) return;

        // Generate UUID for the new list
        const listId = generateUUID();

        // Store in localStorage
        const todoLists = JSON.parse(localStorage.getItem('todoLists') || '{}');
        todoLists[listId] = {
            name: name,
            created: new Date().toISOString()
        };
        localStorage.setItem('todoLists', JSON.stringify(todoLists));

        // Create the list on the server
        const formData = new FormData();
        formData.append('name', name);
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);
        formData.append('list_id', listId);

        try {
            const response = await fetch("{% url 'create_list' %}", {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            if (response.ok) {
                // Clear the input
                nameInput.value = '';

                // Re-render the lists
                renderLists();
            }
        } catch (error) {
            console.error('Error creating list on server:', error);
            // Still show the list in UI even if server save fails
            nameInput.value = '';
            renderLists();
        }
    });

    // Delete list function
    window.deleteList = function(listId) {
        // Remove from localStorage only
        const todoLists = JSON.parse(localStorage.getItem('todoLists') || '{}');
        delete todoLists[listId];
        localStorage.setItem('todoLists', JSON.stringify(todoLists));

        // Also remove from visitedLists
        const visitedLists = JSON.parse(localStorage.getItem('visitedLists') || '{}');
        delete visitedLists[listId];
        localStorage.setItem('visitedLists', JSON.stringify(visitedLists));

        // Re-render the lists
        renderLists();
    }

    // Load lists on page load
    document.addEventListener('DOMContentLoaded', function() {
        renderLists();
    });
</script>
{% endblock %}"""


# List detail template
LIST_DETAIL_TEMPLATE = """{% extends "base.html" %}
{% block title %}{{ todo_list.name }}{% endblock %}
{% block content %}
<div class="app-header">
    <div class="header-row">
        <h1>{{ todo_list.name }}</h1>
        <a href="{% url 'home' %}" class="back-button">← Back</a>
    </div>
</div>

<div class="content">
    <div class="card">
        <form hx-post="{% url 'add_item' todo_list.id %}"
              hx-target="#items"
              hx-swap="beforeend"
              hx-on::after-request="if(event.detail.successful) { this.reset(); this.querySelector('input[name=text]').focus(); }">
            {% csrf_token %}
            <input type="text" name="text" placeholder="Add new item..." required autofocus>
            <button type="submit" class="btn-primary">Add Item</button>
        </form>
    </div>

    <div id="message-container"></div>

    <div class="card">
        <h2>Items</h2>
        <div id="items">
        {% for item in todo_list.items.all %}
        <div class="todo-item" id="item-{{ item.id }}">
            <div class="todo-item-text" id="text-{{ item.id }}">
                {{ item.text }}
            </div>
            <div class="actions">
                <button class="btn-icon btn-edit"
                        hx-get="{% url 'edit_item_form' todo_list.id item.id %}"
                        hx-target="#item-{{ item.id }}"
                        hx-swap="outerHTML"
                        title="Edit">
                    ✏️
                </button>
                <button class="btn-icon btn-delete"
                        hx-delete="{% url 'delete_item' todo_list.id item.id %}"
                        hx-target="#item-{{ item.id }}"
                        hx-swap="outerHTML"
                        title="Delete">
                    🗑️
                </button>
            </div>
        </div>
        {% empty %}
        <div class="empty-state" id="empty-state">
            <p>No items yet. Add your first item above!</p>
        </div>
        {% endfor %}
        </div>
    </div>
</div>

<script>
    // Store this list visit
    storeListVisit('{{ todo_list.id }}', '{{ todo_list.name }}');

    // Update list name from localStorage if available and ensure list is stored
    document.addEventListener('DOMContentLoaded', function() {
        const todoLists = JSON.parse(localStorage.getItem('todoLists') || '{}');
        const listId = '{{ todo_list.id }}';
        const listName = '{{ todo_list.name }}';

        // Check if list exists in localStorage
        if (!todoLists[listId]) {
            // Add this list to localStorage since we're visiting it
            console.log('Adding visited list to localStorage:', listName);
            todoLists[listId] = {
                name: listName,
                created: new Date().toISOString()
            };
            localStorage.setItem('todoLists', JSON.stringify(todoLists));
        } else {
            // List already exists, update the displayed name if localStorage has a different one
            if (todoLists[listId].name) {
                const h1Elements = document.querySelectorAll('h1');
                h1Elements.forEach(h1 => {
                    if (!h1.textContent.includes('Todo Lists')) {
                        h1.textContent = todoLists[listId].name;
                    }
                });
            }
        }
    });
</script>
{% endblock %}"""


# Partial templates for HTMX responses
LIST_ITEM_PARTIAL = """<div class="list-item">
    <a href="{% url 'list_detail' list.id %}"
       onclick="storeListVisit('{{ list.id }}', '{{ list.name }}')">
        {{ list.name }}
    </a>
    <span style="color: #999; font-size: 14px;">
        Created: {{ list.created_at|date:"Y-m-d H:i" }}
    </span>
</div>"""


TODO_ITEM_PARTIAL = """<div class="todo-item" id="item-{{ item.id }}">
    <div class="todo-item-text" id="text-{{ item.id }}">
        {{ item.text }}
    </div>
    <div class="actions">
        <button class="btn-icon btn-edit"
                hx-get="{% url 'edit_item_form' item.todo_list.id item.id %}"
                hx-target="#item-{{ item.id }}"
                hx-swap="outerHTML"
                title="Edit">
            ✏️
        </button>
        <button class="btn-icon btn-delete"
                hx-delete="{% url 'delete_item' item.todo_list.id item.id %}"
                hx-target="#item-{{ item.id }}"
                hx-swap="outerHTML"
                title="Delete">
            🗑️
        </button>
    </div>
</div>"""


EDIT_ITEM_FORM = """<div class="todo-item" id="item-{{ item.id }}">
    <form class="edit-form"
          hx-put="{% url 'update_item' item.todo_list.id item.id %}"
          hx-target="#item-{{ item.id }}"
          hx-swap="outerHTML">
        {% csrf_token %}
        <input type="text" name="text" value="{{ item.text }}" required autofocus>
        <button type="submit" class="btn-icon btn-edit" title="Save">✅</button>
        <button type="button" class="btn-icon btn-delete"
                hx-get="{% url 'cancel_edit' item.todo_list.id item.id %}"
                hx-target="#item-{{ item.id }}"
                hx-swap="outerHTML"
                title="Cancel">
            ❌
        </button>
    </form>
</div>"""


# Register templates
app.templates = {
    "base.html": BASE_TEMPLATE,
    "home.html": HOME_TEMPLATE,
    "list_detail.html": LIST_DETAIL_TEMPLATE,
    "partials/list_item.html": LIST_ITEM_PARTIAL,
    "partials/todo_item.html": TODO_ITEM_PARTIAL,
    "partials/edit_item_form.html": EDIT_ITEM_FORM,
}


# Views
@app.route("/", name="home")
def home(request):
    # Don't fetch lists from server - they'll be loaded from localStorage
    return TemplateResponse(request, "home.html", {})


@app.route("create-list/", name="create_list")
def create_list(request):
    if request.method == "POST":
        from django.utils import timezone
        from datetime import timedelta

        # Clean up old lists (not accessed for 30+ days)
        thirty_days_ago = timezone.now() - timedelta(days=30)

        # Delete lists that haven't been updated in 30 days
        old_lists = TodoList.objects.filter(updated_at__lt=thirty_days_ago)
        deleted_count = old_lists.count()
        if deleted_count > 0:
            print(f"Deleting {deleted_count} old lists that haven't been accessed in 30+ days")
            old_lists.delete()

        name = request.POST.get("name")
        list_id = request.POST.get("list_id")

        if name and list_id:
            # Check if list already exists with this ID
            try:
                todo_list = TodoList.objects.get(id=list_id)
            except TodoList.DoesNotExist:
                # Create new list with the provided UUID
                todo_list = TodoList.objects.create(id=list_id, name=name)

            return HttpResponse("OK")  # Simple response since UI is handled client-side
    return HttpResponse("")


@app.route("list/<uuid:list_id>/", name="list_detail")
def list_detail(request, list_id):
    try:
        todo_list = TodoList.objects.get(id=list_id)
        # Update the timestamp to mark this list as recently accessed
        todo_list.save(update_fields=['updated_at'])
    except TodoList.DoesNotExist:
        # If list doesn't exist on server but user navigated from localStorage,
        # we'll create a placeholder. The actual name will be in localStorage.
        # Get name from localStorage via JavaScript if needed
        todo_list = TodoList.objects.create(
            id=list_id,
            name=f"List {str(list_id)[:8]}"  # Default name using first 8 chars of UUID
        )
    return TemplateResponse(request, "list_detail.html", {"todo_list": todo_list})


@app.route("list/<uuid:list_id>/add-item/", name="add_item")
def add_item(request, list_id):
    if request.method == "POST":
        todo_list = get_object_or_404(TodoList, id=list_id)
        text = request.POST.get("text")
        if text:
            # Check for duplicates (case-insensitive)
            text_stripped = text.strip()
            existing_items = todo_list.items.all()
            for existing_item in existing_items:
                if existing_item.text.lower() == text_stripped.lower():
                    # Return a simple message for duplicate that auto-removes
                    return HttpResponse(
                        '<div class="card" id="duplicate-message" style="background: #fff3cd; border-color: #ffc107; padding: 15px; margin-bottom: 15px;">'
                        '<p style="color: #856404; margin: 0; font-weight: 500;">This item already exists in the list</p>'
                        '<script>setTimeout(() => document.getElementById("duplicate-message")?.remove(), 3000);</script>'
                        '</div>',
                        headers={'HX-Reswap': 'innerHTML', 'HX-Retarget': '#message-container'}
                    )

            item = TodoItem.objects.create(todo_list=todo_list, text=text_stripped)
            # Update the list's timestamp
            todo_list.save(update_fields=['updated_at'])
            # Remove empty state if this is the first item
            response = TemplateResponse(request, "partials/todo_item.html", {"item": item})
            if todo_list.items.count() == 1:
                response["HX-Reswap"] = "innerHTML"
                return response
            return response
    return HttpResponse("")


@app.route("list/<uuid:list_id>/item/<uuid:item_id>/edit-form/", name="edit_item_form")
def edit_item_form(request, list_id, item_id):
    item = get_object_or_404(TodoItem, id=item_id, todo_list_id=list_id)
    return TemplateResponse(request, "partials/edit_item_form.html", {"item": item})


@app.route("list/<uuid:list_id>/item/<uuid:item_id>/", name="update_item")
def update_item(request, list_id, item_id):
    if request.method == "PUT":
        from django.http import QueryDict
        item = get_object_or_404(TodoItem, id=item_id, todo_list_id=list_id)
        # Parse PUT data from request body
        put_data = QueryDict(request.body)
        text = put_data.get("text")
        if text:
            item.text = text
            item.save()
            # Update the list's timestamp
            item.todo_list.save(update_fields=['updated_at'])
        return TemplateResponse(request, "partials/todo_item.html", {"item": item})
    return HttpResponse("")


@app.route("list/<uuid:list_id>/item/<uuid:item_id>/cancel/", name="cancel_edit")
def cancel_edit(request, list_id, item_id):
    item = get_object_or_404(TodoItem, id=item_id, todo_list_id=list_id)
    return TemplateResponse(request, "partials/todo_item.html", {"item": item})


@app.route("list/<uuid:list_id>/item/<uuid:item_id>/delete/", name="delete_item")
def delete_item(request, list_id, item_id):
    if request.method == "DELETE":
        item = get_object_or_404(TodoItem, id=item_id, todo_list_id=list_id)
        todo_list = item.todo_list
        item.delete()

        # Update the list's timestamp
        todo_list.save(update_fields=['updated_at'])

        # If no items left, show empty state
        if not TodoItem.objects.filter(todo_list_id=list_id).exists():
            return HttpResponse('<div class="empty-state" id="empty-state"><p>No items yet. Add your first item above!</p></div>')

        return HttpResponse("")
    return HttpResponse("")


if __name__ == "__main__":
    # For production deployment - use PORT env var if available
    port = int(os.environ.get("PORT", 8000))
    # In production, bind to 0.0.0.0 to accept external connections
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    app.run(host=f"{host}:{port}")