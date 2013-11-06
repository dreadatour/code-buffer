# coding: utf-8
from __future__ import with_statement

import codecs
import errno
import hashlib
import os
import re
import uuid

from pygments import highlight
from pygments.lexers import (
    get_lexer_by_name, guess_lexer, get_all_lexers, TextLexer, ClassNotFound)
from pygments.formatters import HtmlFormatter

from flask import Flask, abort, request, Response, redirect, render_template


app = Flask(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SNIPPETS_DIR = os.path.abspath(os.path.join(PROJECT_ROOT, 'snippets'))

UID_RE = re.compile(r'^[0-9a-fA-F]{32}$')


def lexers_list():
    """
    Get list of pygments lexers.
    """
    lexers = [{'title': lex[0], 'name': lex[1][0]} for lex in get_all_lexers()]
    return sorted(lexers, key=lambda lex: lex['title'].lower())


def snippet_file(uid):
    """
    Get snippet file path by snippet uid.
    """
    return os.path.sep.join((SNIPPETS_DIR, uid[0:2], uid[2:4], uid))


def read_snippet(filename):
    """
    Read snippet file and get user_id, lang, title and code.
    """
    try:
        with codecs.open(filename, 'r', 'utf-8') as snippet:
            content = snippet.readlines()
    except IOError:
        return None

    # simplest check for snippet file format
    if len(content) < 5 or content[3].strip() != u'====8<====':
        return None

    return {
        'user_id': content[0].strip(),
        'lang': content[1].strip(),
        'title': content[2].strip(),
        'code': ''.join(content[4:]).strip(),
    }


def save_snippet(filename, user_id, lang, title, code):
    """
    Save snippet to file.
    """
    # create directory if needed
    dirname = os.path.dirname(filename)
    try:
        os.makedirs(dirname)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(dirname):
            pass
        else:
            app.logger.error("Can't create directory: '%s'" % dirname)
            abort(500)

    # save file
    try:
        with codecs.open(filename, 'w', 'utf-8') as output:
            output.write(u'%s\n' % hashlib.md5(user_id).hexdigest())
            output.write(u'%s\n' % lang)
            output.write(u'%s\n' % title)
            output.write(u'====8<====\n')
            output.write(u'%s\n' % code)
    except IOError:
        app.logger.error("Can't write to file: '%s'" % filename)
        abort(500)


@app.errorhandler(403)
def error_forbidden(e):
    """
    View '403 Forbidden' error.
    """
    return render_template('error.html', code=403), 403


@app.errorhandler(404)
def error_not_found(e):
    """
    View '404 Page not found' error.
    """
    return render_template('error.html', code=404), 404


@app.errorhandler(500)
def error_server(e):
    """
    View '500 Server error' error.
    """
    return render_template('error.html', code=500), 500


@app.route('/save/', methods=['POST'])
def save():
    """
    Save snippet.
    """
    user_id = request.cookies.get('user_id')

    if 'uid' not in request.form:  # this is new snippet
        uid = uuid.uuid4().get_hex()  # generate new snippet uid
        filename = snippet_file(uid)  # generate snippet filename by uid

        if user_id is None:  # this is new user
            user_id = uuid.uuid4().get_hex()  # create new user id
    else:  # edit exists snippet
        uid = request.form.get('uid')
        if not UID_RE.match(uid):
            abort(403)  # uid is bad

        filename = snippet_file(uid)
        if not os.path.isfile(filename):
            abort(403)  # file is not exists

        snippet = read_snippet(filename)
        if snippet is None:
            app.logger.error("Can't read file: '%s'" % filename)
            abort(403)  # file is bad

        if user_id is None or not UID_RE.match(user_id):
            app.logger.error("Cookie user_id is wrong: '%s'" % user_id)
            abort(403)  # user cookie is bad

        if snippet.get('user_id') != hashlib.md5(user_id).hexdigest():
            app.logger.error(
                "User is wrong: '%s' != '%s'" % (user_id, snippet['user_id'])
            )
            abort(403)  # user is wrong

    save_snippet(
        filename,
        user_id,
        request.form.get('lang', '').strip(),
        request.form.get('title', '').strip(),
        request.form.get('code', '').strip()
    )

    # add user_id cookie to response and redirect to 'view snippet' page
    response = app.make_response(redirect('/%s/' % uid))
    response.set_cookie('user_id', value=user_id, max_age=604800)  # one week
    return response


@app.route('/<uid>/', methods=['GET'])
@app.route('/<uid>/raw/', methods=['GET'])
@app.route('/<uid>/edit/', methods=['GET'])
def view(uid):
    """
    View snippet.
    """
    if not UID_RE.match(uid):
        abort(404)  # uid is bad

    filename = snippet_file(uid)
    if not os.path.isfile(filename):
        app.logger.warning("File not found: '%s'" % filename)
        abort(404)  # file is not found

    snippet = read_snippet(filename)
    if snippet is None:
        app.logger.error("Can't read file: '%s'" % filename)
        abort(404)  # file is bad (can't read it)

    code = snippet.get('code', '')

    snippet['uid'] = uid
    user_id = request.cookies.get('user_id')
    if user_id is not None and UID_RE.match(user_id):
        if snippet.get('user_id') == hashlib.md5(user_id).hexdigest():
            snippet['editable'] = True  # user can edit snippet

    if request.path.endswith('/raw/'):  # this is raw snippet view
        return Response(code, content_type='text/plain')

    if request.path.endswith('/edit/'):  # this is 'edit snippet' page
        return render_template('edit.html', lexers=lexers_list(), **snippet)

    # get lexer
    lang = snippet.get('lang')
    if lang == '*auto*':
        if code:
            lexer = guess_lexer(code)
        else:
            lexer = TextLexer()
    elif lang:
        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except ClassNotFound:
            lexer = TextLexer()
    else:
        lexer = TextLexer()
    snippet['lexer'] = lexer.name

    # format code with lexer
    formatter = HtmlFormatter(linenos=True)
    snippet['html'] = highlight(code, lexer, formatter)

    # this is 'view snippet' page
    return render_template('view.html', **snippet)


@app.route('/', methods=['GET'])
def add():
    """
    Edit snippet.
    """
    return render_template('edit.html', lexers=lexers_list())


if __name__ == '__main__':
    app.run()
