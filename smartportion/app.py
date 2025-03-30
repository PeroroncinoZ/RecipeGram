from flask import Flask, render_template, request, redirect, flash, url_for
import sqlite3
from collections import defaultdict
import os
from werkzeug.utils import secure_filename
import json


app = Flask(__name__)
DB_NAME = 'recipes.db'
app.secret_key = 'supersecretkey'
# ---------- DATABASE SETUP ----------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                ingredients TEXT,
                instructions TEXT,
                votes INTEGER DEFAULT 0
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


@app.route('/')
def index():
    ingredients = load_weekly_ingredients()
    return render_template('index.html', ingredients=ingredients)

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    ingredients = load_weekly_ingredients()

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

            c.execute('''
                INSERT INTO recipes (title, ingredients, instructions, image)
                VALUES (?, ?, ?, ?)
            ''', (title, ', '.join(selected_ingredients), instructions, filename))
            conn.commit()

        flash("✅ Recipe submitted successfully!")
        return redirect(url_for('vote'))

    return render_template('submit.html', ingredients=ingredients)

@app.route('/vote', methods=['GET'])
def vote():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row  # enable dict-style access
        c = conn.cursor()
        c.execute('SELECT id, title, ingredients, instructions, votes, image FROM recipes')
        rows = c.fetchall()

        # Convert each row to a dict and fix ingredients
        recipes = []
        for row in rows:
            recipe = dict(row)
            recipe['ingredients'] = [i.strip() for i in recipe['ingredients'].split(',')]
            recipes.append(recipe)

    return render_template('vote.html', recipes=recipes)



@app.route('/vote/<int:recipe_id>', methods=['POST'])
def vote_recipe(recipe_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('UPDATE recipes SET votes = votes + 1 WHERE id = ?', (recipe_id,))
        conn.commit()
    return redirect('/vote')

@app.route('/results')
def results():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT title, votes FROM recipes')
        data = c.fetchall()

    total_votes = sum([row['votes'] for row in data]) or 1
    proportions = [{
        'title': row['title'],
        'votes': row['votes'],
        'percent': round((row['votes'] / total_votes) * 100, 1)
    } for row in data]
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
    return render_template('admin.html')
@app.route('/set_ingredients', methods=['POST'])
def set_ingredients():
    ingredients = [request.form.get(f'ingredient{i}') for i in range(5)]
    with open('weekly_ingredients.json', 'w') as f:
        json.dump([ing for ing in ingredients if ing], f)
    return redirect('/admin')
@app.route('/vote/<int:recipe_id>/like', methods=['POST'])
def vote_recipe_ajax(recipe_id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('UPDATE recipes SET votes = votes + 1 WHERE id = ?', (recipe_id,))
        conn.commit()
        c.execute('SELECT votes FROM recipes WHERE id = ?', (recipe_id,))
        votes = c.fetchone()[0]
    return {'success': True, 'votes': votes}


# ---------- MAIN ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
