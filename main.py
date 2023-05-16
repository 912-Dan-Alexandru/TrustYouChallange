import requests
from requests import RequestException
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import csv

class Book:
    def __init__(self, id, title, categories, authors, description, price):
        self.id = id
        self.title = title
        self.categories = categories
        self.authors = authors
        self.price = price
        self.description = description

    def __dict__(self):
        return {'ID': self.id,
                'Title': self.title,
                'Categories': ';'.join(self.categories),
                'Authors': ';'.join(self.authors),
                'Price': self.price,
                'Description': self.description
                }

def fetch_url(url, params=None):
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        print(f'Error: {e}')
    except Exception as e:
        print(f'Unexpected error: {e}')

    return None

def get_books_by_category(category, limit=1000):
    url = f'https://openlibrary.org/subjects/{category}.json'
    params = {'category': category, 'limit': limit, 'offset': 0}
    books = []

    while True:
        data = fetch_url(url, params)
        if data:
            books.extend(data.get('works', []))
        if not data or len(data.get('works', [])) < limit:
            return books
        params['offset'] += limit


def get_categories(data):
    if isinstance(data, list):
        return list(set(item.split('(')[0].strip() for item in data))
    return []


def get_authors(data):
    authors = []
    if not isinstance(data, list):
        return authors
    for item in data:
        if not item.get('author') or not item.get('author').get('key'):
            continue
        auth_id = item.get('author').get('key').split("/")[2]
        author_info = fetch_url(f'https://openlibrary.org/authors/{auth_id}.json')
        if author_info and author_info.get('name'):
            authors.append(author_info.get('name'))
    return authors

def get_description(data):
    if data.get('description'):
        return data.get('description')
    if data.get('excerpts') and data.get('excerpts')[0].get('excerpt'):
        return data.get('excerpts')[0].get('excerpt').get('value')
    return None

def get_book_info(id):
    url = f'https://openlibrary.org/works/{id}.json'
    data = fetch_url(url)
    title, categories, authors, description = None, None, None, None
    if isinstance(data, dict):
        title = data.get('title')
        categories = get_categories(data.get('subjects')) if data.get('subjects') else []
        authors = get_authors(data.get('authors')) if data.get('authors') else []
        description = get_description(data)
    return title, categories, authors, description

def get_book_price(id, df):
    for _, row in df.iterrows():
        if id == row['Book ID']:
            return row['Price']
    return None

def get_books_objects(categories):
    df = pd.read_csv('book_price.csv')
    book_objects = []
    for category in categories:
        books = get_books_by_category(category)
        print(f'fetching books by category {category}')
        count = 0
        thresh = 10
        for book in books:
            if count*100//len(books) >= thresh:
                print(f'Progress: {thresh}%')
                thresh += 10 * ((count*100//len(books) - thresh)//10 + 1)
            book_id = book["key"].split("/")[2]
            title, categories, authors, description = get_book_info(book_id)
            price = get_book_price(book_id, df)
            book_objects.append(Book(book_id, title, categories, authors, description, price))
            count += 1
    return book_objects

# def generate_csv(books, filename):
#     data = []
#     for book in books:
#         data.append(book.__dict__())
#     df = pd.DataFrame(data)
#     df.to_csv(filename, index=False)
#
# def generate_excel(books, filename):
#     data = []
#     for book in books:
#         data.append(book.__dict__())
#     df = pd.DataFrame(data)
#     df.to_excel(filename, index=False, engine='openpyxl')

def generate_exports(books, csv_filename, excel_filename):
    data = []
    for book in books:
        data.append(book.__dict__())
    df = pd.DataFrame(data)
    df.to_csv(csv_filename, index=False)
    df.to_excel(excel_filename, index=False, engine='openpyxl')

def load_to_spreadsheets(filename):
    df = pd.read_excel(filename)
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scopes)
    client = gspread.authorize(credentials)

    spreadsheet = client.create('Books_Spreadsheet')

    worksheet = spreadsheet.get_worksheet(0)

    data = df.astype(str).values.tolist()
    worksheet.update(data)
    spreadsheet.share('danalex1610@gmail.com', perm_type='user', role='writer')

if __name__ == "__main__":
    categories = ['python', 'database_software', 'relational_databases']
    books = get_books_objects(categories)
    # generate_csv(books, 'books.csv')
    # generate_excel(books, 'books.xlsx')
    generate_exports(books, 'books.csv', 'books.xlsx')
    load_to_spreadsheets('books.xlsx')