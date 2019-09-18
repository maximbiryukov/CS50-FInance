import requests
import urllib.parse
from cs50 import SQL

from datetime import datetime

from flask import redirect, render_template, request, session
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        response = requests.get(f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token=pk_8298737a219842fcbd3d989db6b5e565")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def hash_password(password):
    hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
    return hash

def check_password(password, passconf):
    hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
    if check_password_hash(hash, passconf):
        return True
    else:
        return False

def get_stocks(user_id): # returns list with all stocks owned (just the tickers)
    db = SQL("sqlite:///finance.db")
    stock_list = []
    transactions = db.execute("SELECT * from transactions WHERE user_id = :user", user=user_id)
    for transaction in transactions:
        if transaction["ticker"] not in stock_list:
            stock_list.append(transaction["ticker"])
    return stock_list

def allstocks(user_id): # returns dictionary with stocks and number owned
    db = SQL("sqlite:///finance.db")

    stock_list = []
    stock_dict = {}
    stock_balance = 0
    transactions = db.execute("SELECT * from transactions WHERE user_id = :user", user=session["user_id"])
# stocks owned
    for transaction in transactions:
        if transaction["ticker"] not in stock_list:
            stock_list.append(transaction["ticker"])

    for stock in stock_list:
        for transaction in transactions:
            if transaction["ticker"] == stock and transaction["buy"] == 'True':
                stock_balance += transaction["number"]
            elif transaction["ticker"] == stock and transaction["buy"] == 'False':
                stock_balance -= transaction["number"]
        tmp = {stock : stock_balance}
        stock_dict.update(tmp)
        stock_balance = 0
    return stock_dict

def stock_number(ticker):
    portfolio = allstocks(session["user_id"])
    return portfolio[ticker]

def checkname(username): # returns True if username is not taken
    db = SQL("sqlite:///finance.db")
    namelist = db.execute("SELECT * from users WHERE username = :user", user=username)
    if namelist:
        return False
    else:
        return True

def stockbuyer(ticker, num):
    db = SQL("sqlite:///finance.db")
    stock = lookup(ticker)
    if stock is None:
        return apology("NO SUCH STOCK")
    else:
        price = stock["price"]
        tr_value = float(num) * price
        cash = db.execute("SELECT cash from users WHERE id = :id", id=session["user_id"])

# buy stock if enough cash, if not - return apology
        if (cash[0]["cash"] >= float(num) * price):
            db.execute("INSERT INTO transactions (user_id, ticker, number, datetime, purchase_price, buy) VALUES (:id, :ticker, :number, :datetime, :purchase_price, :buy)", buy="True", id=session["user_id"], ticker=stock["symbol"], number=num, datetime=datetime.now(), purchase_price=stock["price"])
            db.execute("UPDATE users SET cash = :cash WHERE id=:id", cash=cash[0]["cash"] - tr_value, id=session["user_id"])
            return redirect("/")
        else:
            return apology("NOT ENOUGH CASH")