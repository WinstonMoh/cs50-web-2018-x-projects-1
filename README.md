### Project 1

Web Programming with Python and JavaScript
## cs50-web-2018-x-projects-1 - Harvard University

## Introduction
Web application for book reviews. Allows users to create a account and search for a book. Then write reviews for that book. </br>
Doesn't use ORM(Object relational mapping) for database. </br>
@author: Winston Moh T.

## File Contents
- `application.py` - main file for backend stuff.
- `templates/book.html` - displays details of particular book.
- `templates/index.html` - Home page of site.
- `templates/layout.html` - Template for all html files.
- `templates/signup.html` - displays signup page for creating new account.
- `templates/welcome.html` - displays welcome page after login.

## Running the application
Make sure flask is installed on computer. </br>
Create account on heroku and create database. </br>
Set the following environmental variables in terminal: </br>
  `export FLASK_APP=application.py` </br>
  `export FLASK_DEBUG=1` </br>
To run the application execute `flask run` </br>
Finally, open address `127.0.0.1:5000` to access site.
