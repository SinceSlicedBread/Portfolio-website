import os
from flask import Flask, render_template, redirect, url_for, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_bootstrap import Bootstrap5
from flask import flash
import smtplib
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float

# SMTP contact form email info
MY_EMAIL = os.environ.get("MY_EMAIL")
PASSWORD = os.environ.get("PASSWORD")

app = Flask(__name__)
Bootstrap5(app)
app.config['SECRET_KEY'] = os.environ.get("FLASK_KEY")

# Database for portfolio pieces
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI",'sqlite:///portfolio.db')
db = SQLAlchemy(model_class=Base)
db.init_app(app)

class Piece(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True)
    elements: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(String, nullable=False)
    img: Mapped[str] = mapped_column(String)

## Run this code only the first time to create database file
with app.app_context():
    db.create_all()

# Contact form using setup
class ContactForm(FlaskForm):
    name = StringField(label='Name', validators=[DataRequired()], render_kw={"placeholder": "What shall I call you?"})
    email = StringField(label='Email address', validators=[DataRequired(), Email()], render_kw={"placeholder": "To whence shall emails be directed in reply?"})
    message = StringField(label='Message', validators=[DataRequired()], render_kw={"placeholder": "Your missive goes here"})
    submit = SubmitField(label='Dispatch!')

## Add portfolio piece form -- COMMENT OUT ONCE PORTFOLIO COMPLETE
class AddPieceForm(FlaskForm):
    title = StringField(label='Title', validators=[DataRequired()])
    elements = StringField(label='Software Elements', validators=[DataRequired()])
    description = StringField(label='Description', validators=[DataRequired()])
    img = StringField(label='Cover Image')
    submit = SubmitField(label='Add Piece')

@app.route('/portfolio/add', methods = ['GET','POST'])
def add_piece():
    my_form = AddPieceForm()
    if my_form.validate_on_submit():
        flash('Successfully Loaded to Database!')
        title = request.form.get('title')
        elements = request.form.get('elements')
        description = request.form.get('description')
        img = request.form.get('img')
        print(f'{title}\n{elements}\n{description}\n{img}')
        with app.app_context():
            piece = Piece(title=title,
                          elements=elements,
                          description=description,
                          img=img)
            db.session.add(piece)
            db.session.commit()
        return redirect(url_for('portfolio'))
    return render_template('add.html', form=my_form)
## END OF COMMENT OUT SECTION

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/portfolio')
def portfolio():
    with app.app_context():
        result = db.session.execute(db.select(Piece))
        all_pieces = result.scalars().all()
    return render_template('portfolio.html', all_pieces=all_pieces)

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