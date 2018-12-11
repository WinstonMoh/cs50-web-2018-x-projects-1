#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec  5 00:47:19 2018
Project 1. Book review site. Utilizes Flask, HTML, CSS and PostgreSQL
@author: chepson
"""

import os
import re
import cgi
import hashlib
import random
import string
import requests
from flask import Flask, session, render_template, request, escape, url_for, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__, static_url_path='/static')

# Set the secret key to some random bytes. Keep this really secret!
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

# GOODREADS API key:
KEY = "WO7q04Tc6gtQsFYndPkIDw"

# These are the routes that the site must handle.

# This route is the main page of the site
@app.route("/")
def index():
    if 'username' in session:
        return render_template('welcome.html', username=session['username'])
    return render_template("index.html", error = {})

# the login page
@app.route("/login", methods=['POST', 'GET'])
def login():
    errors = {}
    if request.method == 'POST':
        username = request.form.get("username")
        password = request.form.get("password")
        print("user submitted " + username + " pass " + password)
        if valid_login(username, password, errors):
            session['username'] = username
            return redirect(url_for('welcome', username=username))
    # the code below is executed if the request method was GET or the credentials were invalid
    return render_template("index.html", error = errors)

@app.route("/signup")
def signup():
    return render_template("signup.html")

# process the signing up process
@app.route("/signup", methods=['POST', 'GET'])
def process_signup():
    errors = {}
    if request.method == 'POST':
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")
        verify = request.form.get("verify")
        if password != verify:
            errors["password_error"] = "Passwords do not match"
            return render_template("signup.html", error = errors)
        errors = {'username': cgi.escape(username)}
        if validate_signup(email, username, password, errors):
            # check if username already exists
            if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount != 0:
                errors['username_error'] = "Username already in use. Please choose another"
                return render_template("signup.html", error = errors)
            if db.execute("SELECT * FROM users WHERE email = :email", {"email": email}).rowcount != 0:
                errors['email_error'] = "email already in use. Please choose another"
                return render_template("signup.html", error = errors)

        session['username'] = username
        password_hash = make_pw_hash(password)
        db.execute("INSERT INTO users (username, email, password) VALUES (:username, :email, :password)", {"username": username, "email": email, "password": password_hash})
        db.commit()
        return redirect(url_for('welcome', username = username))
    # user did not validate or method is GET
    return render_template("signup.html", error = errors)

# display welcome page
@app.route("/welcome")
@app.route("/welcome/<username>", methods=['POST', 'GET'])
#@app.route("/welcome/<username>/search", methods=['POST', 'GET'])
def welcome(username):
    errors = {}
    if request.method == 'POST':
        isbn = request.form.get("isbn")
        title = request.form.get("title")
        author = request.form.get("author")
        if isbn == '':
            isbn = 'None'
        if title == '':
            title = 'None'
        if author == '':
            author = 'None'
        # psql query
        sql = "SELECT * FROM books WHERE isbn ILIKE '%{0}%' OR title ILIKE '%{1}%' OR author ILIKE '%{2}%'".format(isbn,title,author)
        books = db.execute(sql).fetchall()
        if len(books) == 0:
            errors['search_error'] = "No books found. Try again!"
            return render_template("welcome.html", username = username, error = errors)
        return render_template("welcome.html", username = username, error = errors, books = books)
    # user did not validate or method is GET
    return render_template("welcome.html", username = username, error = errors)

# display details about book
@app.route("/details/<int:book_id>", methods = ['POST', 'GET'])
def details(book_id):
    """ List details about a single book """

    username = session['username']
    errors = {}
    # GET book from database
    book = db.execute("SELECT * FROM books WHERE id = :id", {"id": book_id}).fetchone()

    # GET user_id
    user = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
    user_id = user.id

    # get user IDs and reviews of particular book if available from reviews TABLE
    user_reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book_id}).fetchall()

    # create list of tuple with username, rating and comment text:
    reviews = []
    for review in user_reviews:
        user = db.execute("SELECT * FROM users WHERE id = :id", {"id": review.user_id}).fetchone()
        reviews.append((user.username, review.rating, review.text))

    # Get ratings details of book from GOODREADS API:
    ratings = goodreads_API(book.isbn)

    # ADDING review PART
    if request.method == 'POST':
        # get text details from FORM
        rating = request.form.get("rating")
        text = request.form.get("review")

        # if user already left review for this book, return
        verify = db.execute("SELECT * FROM reviews WHERE user_id = :user_id AND book_id = :book_id", {"user_id": user_id, "book_id": book_id}).fetchall()
        if verify:
            errors['outcome'] = "Already entered Review for this post!"
            return render_template("book.html", username = username, book = book, reviews = reviews, ratings = ratings, error = errors)

        # if text is not good, redirect with errors
        if text == "" or rating == "0":
            errors['outcome'] = "Enter text and rating!"
            return render_template("book.html", username = username, book = book, reviews = reviews, ratings = ratings, error = errors)

        # everything is OK
        db.execute("INSERT INTO reviews (user_id, book_id, rating, text) VALUES(:user_id, :book_id, :rating, :text)", {"user_id": user_id, "book_id": book_id, "rating": rating, "text": text})
        db.commit() # make sure details are saved in db

        errors['outcome'] = 'Review Submitted!'
        reviews.append((username, rating, text))
        return render_template("book.html", username = username, book = book, reviews = reviews, ratings = ratings, error = errors)

    # return to book page with all details
    return render_template("book.html", username = username, book = book, reviews = reviews, ratings = ratings)

# API ACCESS TO get details about particular book
@app.route("/api/<isbn>")
def book_api(isbn):
    """ Return details about a single book """

    # Make sure book exists.
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if book is None:
        return jsonify({"error": "INvalid book ISBN"}), 422

    # Get average rating from my site.
    rows = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).fetchall()
    review_count = len(rows)
    sum = 0
    for data in rows:
        sum += data.rating

    # GET  count and rating from goodreads_API
    (goodreads_count, goodreads_rating) = goodreads_API(book.isbn)

    # Calculate updated review count and rating
    review_count += goodreads_count
    sum += goodreads_count * float(goodreads_rating)
    average_score = sum / review_count

    # Get details of book
    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
        "review_count": review_count,
        "average_score": float("{:0.2f}".format(average_score))
    })

# log out of application
@app.route("/logout")
def logout():
    # remove the username from the session if it's there
    session.pop('username', None)
    return render_template('index.html', error = {})

# Method not found
@app.errorhandler(404)
def not_found(error):
    return render_template("error.html"), 404

# Helper functions

# ACCESSES GOODREADS API
def goodreads_API(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": KEY, "isbns": isbn})
    ratings = ()
    if res.status_code != 200:
        ratings = ("N/A", "N/A")
    else:
        data = res.json()
        ratings_count = data['books'][0]['work_ratings_count']
        average_rating = data['books'][0]['average_rating']
        ratings = (ratings_count, average_rating)
    return ratings

# makes a little salt
def make_salt():
    salt = ""
    for i in range(5):
        salt += random.choice(string.ascii_letters)
    return salt

# implement the function make_pw_hash(name, pw) that returns a hashed password
# of the format:
# HASH(pw + salt),salt
# use sha256
def make_pw_hash(pw, salt=None):
    if salt == None:
        salt = make_salt()
    return hashlib.sha256((pw + salt).encode('utf-8')).hexdigest() + "," + salt

# validates a user login. Returns user record or None
def valid_login(username, password, errors):
    user = None
    try:
        user = db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
    except:
        errors['database_error'] = "Unable to query database for user"
        return False

    if user is None:
        errors['username_error'] = "User not in database"
        return False

    salt = user.password.split(',')[1]
    if user.password != make_pw_hash(password, salt):
        errors['password_error'] = "User password is not a match"
        return False

    # looks good
    return True

# check if user details meet criteria
def validate_signup(email, username, password, errors):
    USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
    PASS_RE = re.compile(r"^.{3,20}$")
    EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

    if not USER_RE.match(username):
        errors['username_error'] = "invalid username. try just letters and numbers"
        return False
    if not PASS_RE.match(password):
        errors['password_error'] = "invalid password."
        return False
    if email != "":
        if not EMAIL_RE.match(email):
            errors['email_error'] = "invalid email address"
            return False
    return True
