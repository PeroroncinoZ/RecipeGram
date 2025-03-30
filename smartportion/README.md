📦 SmartPortion

Helping schools reduce cafeteria food waste with student-powered recipe voting.

🍽️ What is SmartPortion?

SmartPortion is a web app that empowers students to vote on school meal recipes using weekly USDA-required ingredients. It helps reduce cafeteria food waste by making meals more appealing and student-approved. Built for school communities to create, vote, and improve school lunches together.

💡 Features

✅ Student login via School ID

📤 Recipe submission with images and selected ingredients

👍 Voting system (1 like per student, toggleable)

📊 Live results with vote percentages

📝 Feedback form to share hunger levels and meal satisfaction

🛠️ Admin panel:

Reset recipes

Set weekly ingredients

Auto-upload or attach ingredient images

Manage/delete users

🚀 Getting Started

Prerequisites

Python 3.11+

pip

1. Clone the repo

git clone https://github.com/FWT-bs/smartportion.git
cd smartportion

2. Install dependencies

pip install -r requirements.txt

3. Run the app

python app.py

Go to http://127.0.0.1:5000 in your browser.

🖼️ Screenshots

Submit Page

Vote Page

Admin Panel







🧪 Tech Stack

Backend: Flask, SQLite

Frontend: Tailwind CSS, HTML

Tools: Jinja, Werkzeug, JSON

⚙️ Admin Access

To access the admin panel, log in with:

School ID: admin
Password: adminpassword (or whatever you configured)

You can reset recipes, set weekly ingredients, and manage users from /admin.

📁 File Structure

smartportion/
├── static/
│   ├── uploads/              # Uploaded recipe + ingredient images
│   └── dist/output.css       # Tailwind output
├── templates/                # HTML templates
├── app.py                    # Main Flask app
├── image_utils.py            # Handles ingredient image downloads
├── weekly_ingredients.json   # Saved weekly ingredient list
└── README.md                 # You're here

🧠 Inspiration

Inspired by USDA food waste reports and student surveys, SmartPortion gives students a voice in school lunch decisions. By letting them vote on recipes made with required ingredients, schools can cut waste and improve satisfaction.

📣 Future Improvements



📜 License

MIT License. Feel free to fork, remix, and build on this!

