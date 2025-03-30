# This Flask app powers BITE – a platform that lets students vote on and submit recipes,
# aiming to reduce school cafeteria food waste.
from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests
import sqlite3
from collections import defaultdict
import os
from werkzeug.utils import secure_filename
import json
import datetime


app = Flask(__name__)
DB_NAME = 'recipes.db'
app.secret_key = 'supersecretkey'
# ---------- DATABASE SETUP ----------
UPLOAD_FOLDER = 'static/uploads'

# Initialize the SQLite database and ensure required tables exist:
# - recipes: stores student-submitted recipes
# - users: stores school ID logins
# - votes: stores recipe likes (one per user per recipe)
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # Recipes table
        c.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                ingredients TEXT,
                instructions TEXT,
                votes INTEGER DEFAULT 0,
                image TEXT,
                submitted_by TEXT
            )
        ''')

        # Users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # 🔧 Add "name" column to existing users table if missing
        try:
            c.execute("ALTER TABLE users ADD COLUMN name TEXT")
        except sqlite3.OperationalError:
            pass  # already exists

        # Votes table
        c.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                user_id INTEGER,
                recipe_id INTEGER,
                UNIQUE(user_id, recipe_id)
            )
        ''')

        conn.commit()


# ---------- ROUTES ----------
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

def load_weekly_ingredients():
    try:
        with open('weekly_ingredients.json') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def allowed_file(filename):
    return (
        '.' in filename and 
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        school_id = request.form['school_id']
        password = request.form['password']

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id, school_id, name FROM users WHERE school_id = ? AND password = ?", (school_id, password))
            user = c.fetchone()

            if user:
                session['user_id'] = user[0]
                session['school_id'] = user[1]
                session['name'] = user[2]  # 👈 this is the key part

                flash("✅ Logged in successfully.")
                return redirect(url_for('index'))
            else:
                flash("❌ Invalid school ID or password.")
                return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        school_id = request.form['school_id']
        password = request.form['password']
        name = request.form['name']

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (school_id, password, name) VALUES (?, ?, ?)",
                          (school_id, password, name))
                conn.commit()
                flash("✅ Account created! Please log in.")
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash("❌ That School ID is already registered.")
                return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if session.get('school_id') != 'admin':
        flash("❌ Admin access only.")
        return redirect(url_for('index'))

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        c.execute("DELETE FROM votes WHERE user_id = ?", (user_id,))
        conn.commit()

    flash("✅ User deleted.")
    return redirect(url_for('admin'))



@app.route('/')
def index():
    ingredient_names = load_weekly_ingredients()

    ingredients = []
    for name in ingredient_names:
        formatted_name = name.strip().title()
        image_path = f"/static/uploads/{name.strip().lower()}.jpg"  # Try to load locally
        ingredients.append({
            'name': formatted_name,
            'image': image_path
        })

    return render_template('index.html', ingredients=ingredients)




# Handles both displaying the recipe submission form and processing recipe uploads.
# Requires login. Saves uploaded images and recipe info to the database.
@app.route('/submit', methods=['GET', 'POST'])
def submit():
    ingredients = load_weekly_ingredients()

    # 🔐 Require login
    if 'user_id' not in session:
        flash("❌ You must be logged in to submit a recipe.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title', '')
        selected_ingredients = request.form.getlist('ingredients')
        instructions = request.form.get('instructions', '')
        file = request.files.get('photo')

        # Validate file presence
        if not file or file.filename == '':
            flash("❌ No file uploaded.")
            return render_template('submit.html',
                                   ingredients=ingredients,
                                   title=title,
                                   selected_ingredients=selected_ingredients,
                                   instructions=instructions)

        filename = secure_filename(file.filename)
        if not allowed_file(filename):
            flash("❌ Only .jpg, .jpeg, or .png files are allowed.")
            return render_template('submit.html',
                                   ingredients=ingredients,
                                   title=title,
                                   selected_ingredients=selected_ingredients,
                                   instructions=instructions)

        # Save file
        filepath = os.path.join('static/uploads', filename)
        file.save(filepath)

        # Save to DB
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            try:
                c.execute("ALTER TABLE recipes ADD COLUMN image TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                c.execute("ALTER TABLE recipes ADD COLUMN submitted_by TEXT")
            except sqlite3.OperationalError:
                pass

            submitted_by = session.get('school_id', 'Anonymous')
            full_title = f"{title} by {session.get('name', submitted_by)}"

            c.execute('''
            INSERT INTO recipes (title, ingredients, instructions, image, submitted_by)
            VALUES (?, ?, ?, ?, ?)
            ''', (full_title, ', '.join(selected_ingredients), instructions, filename, submitted_by))

            conn.commit()

        flash("✅ Recipe submitted successfully!")
        return redirect(url_for('vote'))

    return render_template('submit.html', ingredients=ingredients)
# Displays all recipes for logged-in users to vote on.
# Recipes are marked if the user has already liked them.
@app.route('/vote', methods=['GET'])
def vote():
    if 'user_id' not in session:
        flash("❌ Please log in to vote.")
        return redirect(url_for('login'))

    user_id = session['user_id']

    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM recipes')
        rows = c.fetchall()

        recipes = []
        for row in rows:
            recipe = dict(row)
            recipe['ingredients'] = [i.strip() for i in recipe['ingredients'].split(',')]
            # Mark if this user already liked it
            c.execute('SELECT 1 FROM votes WHERE user_id = ? AND recipe_id = ?', (user_id, row['id']))
            recipe['liked_by_user'] = c.fetchone() is not None
            recipes.append(recipe)

    return render_template('vote.html', recipes=recipes)




@app.route('/vote/<int:recipe_id>', methods=['POST'])
def vote_recipe(recipe_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('UPDATE recipes SET votes = votes + 1 WHERE id = ?', (recipe_id,))
        conn.commit()
    return redirect('/vote')

# Displays a sorted leaderboard of recipes by number of votes.
# Useful for admins to see which meals students prefer.
@app.route('/results')
def results():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT title, votes FROM recipes')
        data = c.fetchall()

    total_votes = sum([row['votes'] for row in data]) or 1
    proportions = sorted([
        {
            'title': row['title'],
            'votes': row['votes'],
            'percent': round((row['votes'] / total_votes) * 100, 1)
        }
        for row in data
    ], key=lambda x: x['votes'], reverse=True)

    return render_template('results.html', proportions=proportions)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        student_name = request.form['student_name']
        hunger_level = request.form['hunger_level']
        portion_choice = request.form['portion_choice']
        feedback_text = request.form['feedback']
        submission_date = datetime.date.today()

        with sqlite3.connect('portion.db') as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    hunger_level TEXT,
                    portion_choice TEXT,
                    feedback TEXT,
                    submission_date DATE
                )
            ''')
            c.execute('''
                INSERT INTO feedback (student_name, hunger_level, portion_choice, feedback, submission_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_name, hunger_level, portion_choice, feedback_text, submission_date))
            conn.commit()
        return redirect('/')
    return render_template('feedback.html')
@app.route('/reset_recipes', methods=['POST'])
def reset_recipes():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM recipes')
        conn.commit()
    return redirect('/')
@app.route('/admin')
def admin():
    if session.get('school_id') != 'admin':
        flash("❌ Admin access only.")
        return redirect(url_for('index'))

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, school_id FROM users")
        users = c.fetchall()

    return render_template('admin.html', users=users)


@app.route('/set_ingredients', methods=['POST'])
def set_ingredients():
    ingredients = []
    os.makedirs('static/uploads', exist_ok=True)

    for i in range(5):
        name = request.form.get(f'ingredient{i}')
        image = request.files.get(f'image{i}')
        if name:
            ingredients.append(name.strip())
            if image and image.filename != '':
                ext = image.filename.rsplit('.', 1)[-1].lower()
                if ext in ['jpg', 'jpeg', 'png']:
                    filename = f"{name.strip().lower()}.jpg"
                    path = os.path.join('static/uploads', filename)
                    image.save(path)

    with open('weekly_ingredients.json', 'w') as f:
        json.dump(ingredients, f)

    flash("✅ Ingredients and images updated successfully.")
    return redirect('/admin')

# AJAX-based toggle for liking or unliking a recipe.
# Updates vote count dynamically.
@app.route('/vote/<int:recipe_id>/like', methods=['POST'])
def vote_recipe_ajax(recipe_id):
    if 'user_id' not in session:
        return {'success': False, 'error': 'Not logged in'}

    user_id = session['user_id']
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        # Check if the user already liked the recipe
        c.execute("SELECT * FROM votes WHERE user_id = ? AND recipe_id = ?", (user_id, recipe_id))
        existing_vote = c.fetchone()

        if existing_vote:
            # User already liked it → remove the like
            c.execute("DELETE FROM votes WHERE user_id = ? AND recipe_id = ?", (user_id, recipe_id))
            c.execute("UPDATE recipes SET votes = votes - 1 WHERE id = ?", (recipe_id,))
        else:
            # User has not liked it yet → add the like
            c.execute("INSERT INTO votes (user_id, recipe_id) VALUES (?, ?)", (user_id, recipe_id))
            c.execute("UPDATE recipes SET votes = votes + 1 WHERE id = ?", (recipe_id,))
        
        conn.commit()

        # Fetch updated vote count
        c.execute("SELECT votes FROM recipes WHERE id = ?", (recipe_id,))
        votes = c.fetchone()[0]

    return {'success': True, 'votes': votes, 'liked': not existing_vote}


@app.route('/logout')
def logout():
    session.clear()
    flash("✅ You have been logged out.")
    return redirect(url_for('login'))
@app.route('/view_feedback')
def view_feedback():
    if session.get('school_id') != 'admin':
        flash("❌ Admin access only.")
        return redirect(url_for('index'))

    with sqlite3.connect('portion.db') as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM feedback ORDER BY submission_date DESC')
        feedback_entries = c.fetchall()

    return render_template('view_feedback.html', feedback=feedback_entries)


# ---------- MAIN ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
