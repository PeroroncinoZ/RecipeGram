from flask import Flask, render_template, request, redirect
import sqlite3
from collections import defaultdict

app = Flask(__name__)
DB_NAME = 'recipes.db'

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

@app.route('/')
def index():
    ingredients = ["Apples", "Carrots", "Bananas", "Spinach", "Strawberries"]
    return render_template('index.html', ingredients=ingredients)

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    ingredients = ["Apples", "Carrots", "Bananas", "Spinach", "Strawberries"]
    if request.method == 'POST':
        title = request.form['title']
        ingredients_str = ', '.join(request.form.getlist('ingredients'))
        instructions = request.form['instructions']

        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO recipes (title, ingredients, instructions)
                VALUES (?, ?, ?)
            ''', (title, ingredients_str, instructions))
            conn.commit()
        return redirect('/vote')
    return render_template('submit.html', ingredients=ingredients)

@app.route('/vote', methods=['GET'])
def vote():
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row  # <-- enables dict-style access
        c = conn.cursor()
        c.execute('SELECT id, title, ingredients, instructions, votes FROM recipes')
        recipes = c.fetchall()
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

# ---------- MAIN ----------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
