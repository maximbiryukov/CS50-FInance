import os
import json

from cs50 import SQL
from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, check_password, hash_password, get_stocks, allstocks, stock_number, checkname, stockbuyer

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "POST":
        if not request.form.get("shares"):
            return apology("How many do you want to buy?")
        else:
            num = request.form.get("shares")
            if num.isdigit() == False:
                return apology("Number should be positive integer")
            elif int(num) <= 0:
                return apology("Number should be positive integer")

        ticker = request.form.get("button")
        return stockbuyer(ticker, request.form.get("shares"))
    else:
        # get transaction data via SQL
        users = db.execute("SELECT cash from users WHERE id = :user", user=session["user_id"])

        stock_list = []
        stock_dict = allstocks(session["user_id"])

    # stock (incl cash), number of shares owned, current price, current value of stock, total account balance
        shares_dict = {}
        cash_total_dict = {}
        total = 0
        for key in stock_dict:
            stock_info = lookup(key)
            tmp2 = {key: [stock_info["name"], stock_dict[key], usd(stock_info["price"]), usd(stock_dict[key] * stock_info["price"])]}
            shares_dict.update(tmp2)
            total += stock_dict[key] * stock_info["price"]
        cash_total_dict.update({"cash": [" ", " ", " ", usd(users[0]["cash"])]})
        cash_total_dict.update({"Total": [" ", " ", " ", usd(total + users[0]["cash"])]})
        ASSETS = shares_dict.items()
        CASHTOTAL = cash_total_dict.items()

        return render_template("index.html", ASSETS=ASSETS, CASHTOTAL=CASHTOTAL)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Choose a stock to buy")
        elif not request.form.get("shares"):
            return apology("How many do you want to buy?")
        else:
            num = request.form.get("shares")
            if num.isdigit() == False:
                return apology("Number should be positive integer")
            elif int(num) <= 0:
                return apology("Number should be positive integer")

        ticker = request.form.get("symbol")

        return stockbuyer(ticker, request.form.get("shares"))

    else:
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():

    if(len(request.args.get('username'))>1):

        if checkname(request.args.get('username')):
            return jsonify(True), 200
        else:
            return jsonify(False), 200

    else:
        return apology("Username should be at least length 1")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # buy/sell, ticker, transaction price, number, datetime
    transactions = db.execute("SELECT * from transactions WHERE user_id = :user", user=session["user_id"])
    output = []
    for transaction in transactions:
        output.append([transaction["buy"], transaction["ticker"], transaction["purchase_price"], transaction["number"], transaction["datetime"]])

    return render_template("history.html", ITEMS=output)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        if stock is None:
            return apology("NO SUCH STOCK", 400)
        else:
            return render_template("quoted.html", name=stock["name"], quote=usd(stock["price"]), ticker=stock["symbol"]), 200
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # proper inputs
        if not checkname(request.form.get("username")):
            return apology("username taken", 400)

        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        elif not request.form.get("confirmation"):
            return apology("must confirm password", 400)

        # Ensure passwords match
        elif (request.form.get("password") != request.form.get("confirmation")):
            return apology("passwords must match", 400)

        hash = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        user = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash=hash)
        session["user_id"] = user
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":

        ticker = request.form.get("symbol")
        number = request.form.get("shares")

        if not ticker:
            return apology("Choose a stock to sell")
        elif not number:
            return apology("Choose number of stocks to sell")

        elif not number.isdigit() or int(number) <= 0:
            return apology("Number of stocks should be a positive integer")

        elif (stock_number(ticker) < int(number)):
            return apology("Not enough stocks")

        else:
            stock = lookup(ticker)
            db.execute("INSERT INTO transactions (user_id, ticker, number, datetime, purchase_price, buy) VALUES (:id, :ticker, :number, :datetime, :purchase_price, :buy)", buy="False", id=session["user_id"], ticker=ticker, number=int(number), datetime=datetime.now(), purchase_price=stock["price"])

            price = stock["price"]
            tr_value = int(number) * price
            cash = db.execute("SELECT cash from users WHERE id = :id", id=session["user_id"])
            db.execute("UPDATE users SET cash = :cash WHERE id=:id", cash=cash[0]["cash"] + tr_value, id=session["user_id"])

            return redirect("/")

    else:

        STOCKS = get_stocks(session["user_id"])
        return render_template("sell.html", STOCKS=STOCKS)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
