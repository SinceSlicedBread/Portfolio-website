import os
from flask import Flask, render_template, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_avatars import Avatars
from flask import flash
from flask_ckeditor import CKEditorField
import smtplib
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Text
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash


# SMTP contact form email info
MY_EMAIL = os.environ.get("MY_EMAIL")
PASSWORD = os.environ.get("PASSWORD")

app = Flask(__name__)
Bootstrap5(app)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")
ckeditor = CKEditor(app)

# Create and initialise login manager
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

avatars = Avatars(app)

# Database for portfolio pieces
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI",'sqlite:///portfolio.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Create tables (Piece, User, Comment)
class Piece(db.Model):
    __tablename__ = "portfolio_pieces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title: Mapped[str] = mapped_column(String(250), unique=True)
    elements: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(String, nullable=False)
    img: Mapped[str] = mapped_column(String)
    comments = relationship("Comment", back_populates="parent_post")
    git: Mapped[str] = mapped_column(String)

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password: Mapped[str] = mapped_column(String(100))
    posts = relationship("Piece", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")

class Comment(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    # child relationship to User
    author_id: Mapped[int] = mapped_column(Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    # child relationship to Piece
    post_id: Mapped[int] =  mapped_column(Integer, db.ForeignKey("portfolio_pieces.id"))
    parent_post = relationship("Piece", back_populates="comments")


## Run this code only the first time to create database file
# with app.app_context():
#     db.create_all()

# Register form
class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(),Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign Me Up!")

# Login form
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let Me In!")

# Contact form using setup
class ContactForm(FlaskForm):
    name = StringField(label='Name', validators=[DataRequired()], render_kw={"placeholder": "What shall I call you?"})
    email = StringField(label='Email address', validators=[DataRequired(), Email()], render_kw={"placeholder": "To whence shall emails be directed in reply?"})
    message = StringField(label='Message', validators=[DataRequired()], render_kw={"placeholder": "Your missive goes here"})
    submit = SubmitField(label='Dispatch!')

## Add portfolio piece form -- add admin authentication
class AddPieceForm(FlaskForm):
    title = StringField(label='Title', validators=[DataRequired()])
    elements = StringField(label='Software Elements', validators=[DataRequired()])
    description = StringField(label='Description', validators=[DataRequired()])
    img = StringField(label='Cover Image')
    git = StringField(label='GitHub URL')
    submit = SubmitField(label='Add Piece')

class CommentForm(FlaskForm):
    text = CKEditorField("Comment", validators=[DataRequired()])
    submit = SubmitField("Submit Comment")

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        password = form.password.data
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        # if email doesn't exist
        if not user:
            flash("I can't find you in our system, please would you register as a new user.")
            return redirect(url_for('register'))
        # if password is incorrect
        elif not check_password_hash(user.password, password):
            flash("Incorrect password entered, please retry.")
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('portfolio'))
    return render_template('login.html', form=form, current_user=current_user)

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # check if user is already registered
        result = db.session.execute(db.select(User).where(User.email == form.email.data))
        user = result.scalar()
        if user:
            flash("You are already registered on the system. Please login instead.")
            return redirect(url_for('login'))
        # if not registered, create new user and login
        else:
            encrypted_password = generate_password_hash(form.password.data,
                                                        method='pbkdf2:sha256',
                                                        salt_length=9
                                                        )
            new_user = User(
                name=form.name.data,
                email=form.email.data,
                password=encrypted_password,
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('portfolio'))
    return render_template("register.html", form=form, current_user=current_user)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/portfolio/add', methods = ['GET','POST'])
def add_piece():
    my_form = AddPieceForm()
    if my_form.validate_on_submit():
        flash('Successfully Loaded to Database!')
        title = request.form.get('title')
        elements = request.form.get('elements')
        description = request.form.get('description')
        img = request.form.get('img')
        git = request.form.get('git')
        print(f'{title}\n{elements}\n{description}\n{img}')
        with app.app_context():
            piece = Piece(title=title,
                          elements=elements,
                          description=description,
                          img=img,
                          author=current_user,
                          git=git)
            db.session.add(piece)
            db.session.commit()
        return redirect(url_for('portfolio'))
    return render_template('add.html', form=my_form)
## END OF admin SECTION

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/portfolio')
def portfolio():
    with app.app_context():
        result = db.session.execute(db.select(Piece))
        all_pieces = result.scalars().all()
    return render_template('portfolio.html', all_pieces=all_pieces, current_user=current_user)

@app.route('/portfolio/<int:piece_id>', methods=['GET', 'POST'])
def show_piece(piece_id):
    piece = db.get_or_404(Piece, piece_id)
    git_url = piece.git
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("Please log in to be able to comment.")
            return redirect(url_for('login.html'))
        else:
            new_comment = Comment(
                text=form.text.data,
                comment_author=current_user,
                parent_post=piece,
            )
            db.session.add(new_comment)
            db.session.commit()
    return render_template('piece.html', piece=piece, form=form, current_user=current_user, git_url=git_url)

@app.route('/contact', methods = ['GET','POST'])
def contact():
    my_form = ContactForm()
    if my_form.validate_on_submit():
        flash('Message successfully sent!')
        user_name = request.form.get('name')
        user_email = request.form.get('email')
        user_message = request.form.get('message')

        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(user=MY_EMAIL, password=PASSWORD)
            connection.sendmail(from_addr=user_email,
                                to_addrs=MY_EMAIL,
                                msg=f"Subject: Developer site contact from {user_name}\n\n"
                                    f"{user_message}\n\n"
                                    f"Reply to: {user_email}")
        return redirect(url_for('contact'))
    return render_template('contact.html', form=my_form)


if __name__ == "__main__":
    app.run(debug=True)