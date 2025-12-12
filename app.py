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
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        h1 {
            color: #333;
            margin-bottom: 10px;
        }

        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .form-group {
            margin-bottom: 15px;
        }

        input[type="text"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }

        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }

        button:hover {
            background: #0056b3;
        }

        button.delete {
            background: #dc3545;
            padding: 5px 10px;
            font-size: 14px;
        }

        button.delete:hover {
            background: #c82333;
        }

        button.edit {
            background: #ffc107;
            color: #333;
            padding: 5px 10px;
            font-size: 14px;
            margin-right: 5px;
        }

        button.edit:hover {
            background: #e0a800;
        }

        .list-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .list-item a {
            color: #007bff;
            text-decoration: none;
            font-size: 18px;
        }

        .list-item a:hover {
            text-decoration: underline;
        }

        .todo-item {
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .todo-item-text {
            flex: 1;
            margin-right: 10px;
        }

        .actions {
            display: flex;
            gap: 5px;
        }

        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #007bff;
            text-decoration: none;
        }

        .back-link:hover {
            text-decoration: underline;
        }

        .edit-form {
            display: flex;
            gap: 10px;
            flex: 1;
        }

        .edit-form input {
            flex: 1;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
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
    {% block content %}{% endblock %}
</body>
</html>"""


# Home page template
HOME_TEMPLATE = """{% extends "base.html" %}
{% block title %}Todo Lists - Home{% endblock %}
{% block content %}
<div class="header">
    <h1>My Todo Lists</h1>
    <p>Create and manage your todo lists</p>
</div>

<div class="container">
    <form id="create-list-form">
        {% csrf_token %}
        <div class="form-group">
            <input type="text" name="name" id="list-name" placeholder="Enter list name..." required>
        </div>
        <button type="submit">Create New List</button>
    </form>
</div>

<div class="container" style="margin-top: 20px;">
    <h2>My Lists</h2>
    <div id="lists">
        <div class="empty-state">
            <p>Loading lists from local storage...</p>
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
            const createdDate = new Date(list.created).toLocaleString();
            return `
                <div class="list-item">
                    <a href="/list/${id}/" onclick="storeListVisit('${id}', '${list.name}')">
                        ${list.name}
                    </a>
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span style="color: #999; font-size: 14px;">
                            Created: ${createdDate}
                        </span>
                        <button class="delete" onclick="deleteList('${id}')" style="padding: 5px 10px;">
                            Remove
                        </button>
                    </div>
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
        if (!confirm('Are you sure you want to remove this list from your view?')) {
            return;
        }

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
{% block title %}{{ todo_list.name }} - Todo List{% endblock %}
{% block content %}
<div class="header">
    <a href="{% url 'home' %}" class="back-link">← Back to Lists</a>
    <h1>{{ todo_list.name }}</h1>
    <p>Manage items in this list</p>
</div>

<div class="container">
    <form hx-post="{% url 'add_item' todo_list.id %}"
          hx-target="#items"
          hx-swap="beforeend"
          hx-on::after-request="if(event.detail.successful) this.reset()">
        {% csrf_token %}
        <div class="form-group">
            <input type="text" name="text" placeholder="Add new item..." required>
        </div>
        <button type="submit">Add Item</button>
    </form>
</div>

<div class="container" style="margin-top: 20px;">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
        <h2 style="margin: 0;">Items</h2>
        <span style="color: #666; font-size: 14px;">
            Last changed: {{ todo_list.updated_at|date:"Y-m-d H:i:s" }}
        </span>
    </div>
    <div id="items">
        {% for item in todo_list.items.all %}
        <div class="todo-item" id="item-{{ item.id }}">
            <div class="todo-item-text" id="text-{{ item.id }}">
                {{ item.text }}
            </div>
            <div class="actions">
                <button class="edit"
                        hx-get="{% url 'edit_item_form' todo_list.id item.id %}"
                        hx-target="#item-{{ item.id }}"
                        hx-swap="outerHTML">
                    Edit
                </button>
                <button class="delete"
                        hx-delete="{% url 'delete_item' todo_list.id item.id %}"
                        hx-target="#item-{{ item.id }}"
                        hx-swap="outerHTML">
                    Delete
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
        <button class="edit"
                hx-get="{% url 'edit_item_form' item.todo_list.id item.id %}"
                hx-target="#item-{{ item.id }}"
                hx-swap="outerHTML">
            Edit
        </button>
        <button class="delete"
                hx-delete="{% url 'delete_item' item.todo_list.id item.id %}"
                hx-target="#item-{{ item.id }}"
                hx-swap="outerHTML">
            Delete
        </button>
    </div>
</div>"""


EDIT_ITEM_FORM = """<div class="todo-item" id="item-{{ item.id }}">
    <form class="edit-form"
          hx-put="{% url 'update_item' item.todo_list.id item.id %}"
          hx-target="#item-{{ item.id }}"
          hx-swap="outerHTML">
        {% csrf_token %}
        <input type="text" name="text" value="{{ item.text }}" required>
        <button type="submit">Save</button>
        <button type="button"
                hx-get="{% url 'cancel_edit' item.todo_list.id item.id %}"
                hx-target="#item-{{ item.id }}"
                hx-swap="outerHTML">
            Cancel
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
            item = TodoItem.objects.create(todo_list=todo_list, text=text)
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
        item = get_object_or_404(TodoItem, id=item_id, todo_list_id=list_id)
        text = request.POST.get("text")
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