import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional
from werkzeug.security import generate_password_hash, check_password_hash

# ====================== APP SETUP ======================
app = Flask(__name__)

# Secret Key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set. Add it in Railway Variables.")

# ====================== DATABASE CONFIG ======================
# Prefer DATABASE_URL (PostgreSQL on Railway)
database_url = os.environ.get('DATABASE_URL')

if not database_url:
    # Fallback to MySQL (ensure env vars are set)
    db_host = os.environ.get('MYSQLHOST')
    db_user = os.environ.get('MYSQLUSER')
    db_password = os.environ.get('MYSQLPASSWORD')
    db_name = os.environ.get('MYSQLDATABASE')
    db_port = os.environ.get('MYSQLPORT', '3306')

    if not all([db_host, db_user, db_password, db_name]):
        raise ValueError("Database variables not set. Add MYSQLHOST, MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE in Railway Variables.")

    database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize DB
db = SQLAlchemy(app)

# ====================== FLASK-LOGIN ======================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ====================== MODELS ======================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=True)
    year = db.Column(db.Integer, nullable=True)
    copies_available = db.Column(db.Integer, default=1)
    description = db.Column(db.Text, nullable=True)

# ====================== FORMS ======================
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=150)])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    isbn = StringField('ISBN', validators=[Optional()])
    year = IntegerField('Year Published', validators=[Optional()])
    copies_available = IntegerField('Copies Available', default=1)
    description = TextAreaField('Description')
    submit = SubmitField('Save Book')

# ====================== ROUTES ======================
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        hashed = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Welcome to Kampala City Library!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
@login_required
def dashboard():
    books = Book.query.all()
    return render_template('dashboard.html', books=books, user=current_user)

@app.route('/books')
@login_required
def books_view():
    books = Book.query.all()
    return render_template('books.html', books=books)

@app.route('/book/new', methods=['GET', 'POST'])
@login_required
def new_book():
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            title=form.title.data,
            author=form.author.data,
            isbn=form.isbn.data,
            year=form.year.data,
            copies_available=form.copies_available.data,
            description=form.description.data
        )
        db.session.add(book)
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('books_view'))
    return render_template('book_form.html', form=form, title='Add New Book')

@app.route('/book/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm(obj=book)
    if form.validate_on_submit():
        book.title = form.title.data
        book.author = form.author.data
        book.isbn = form.isbn.data
        book.year = form.year.data
        book.copies_available = form.copies_available.data
        book.description = form.description.data
        db.session.commit()
        flash('Book updated!', 'success')
        return redirect(url_for('books_view'))
    return render_template('book_form.html', form=form, title='Edit Book')

@app.route('/book/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted.', 'danger')
    return redirect(url_for('books_view'))

# ====================== CREATE TABLES ON STARTUP ======================
with app.app_context():
    db.create_all()

# ====================== RUN APP ======================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)