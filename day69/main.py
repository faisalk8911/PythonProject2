import os
import hashlib

from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    abort
)

from flask_ckeditor import (
    CKEditor,
    CKEditorField
)

from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    current_user
)

from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm

from sqlalchemy import ForeignKey
from sqlalchemy.exc import IntegrityError

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from wtforms import (
    StringField,
    PasswordField,
    SubmitField
)

from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    URL
)


# -----------------------------
# DATABASE BASE
# -----------------------------

class Base(DeclarativeBase):
    pass


# -----------------------------
# DATABASE
# -----------------------------

db = SQLAlchemy(
    model_class=Base
)


# -----------------------------
# FLASK APP
# -----------------------------

app = Flask(__name__)

app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "sqlite:///posts.db"

app.config[
    "SECRET_KEY"
] = os.environ.get(
    "FLASK_SECRET_KEY",
    "development-only-key"
)

db.init_app(app)


# -----------------------------
# CKEDITOR
# -----------------------------

ckeditor = CKEditor(app)


# -----------------------------
# GRAVATAR HELPER
# -----------------------------

def gravatar_url(
    email,
    size=100
):

    clean_email = (
        email
        .strip()
        .lower()
    )

    email_hash = hashlib.md5(
        clean_email.encode("utf-8")
    ).hexdigest()

    return (
        "https://www.gravatar.com/avatar/"
        f"{email_hash}"
        f"?s={size}&d=retro&r=g"
    )


app.jinja_env.globals[
    "gravatar_url"
] = gravatar_url


# -----------------------------
# FLASK LOGIN
# -----------------------------

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = "login"


# -----------------------------
# USER TABLE
# -----------------------------

class User(
    UserMixin,
    db.Model
):

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    email: Mapped[str] = mapped_column(
        unique=True,
        nullable=False
    )

    password: Mapped[str] = mapped_column(
        nullable=False
    )

    name: Mapped[str] = mapped_column(
        nullable=False
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="comment_author"
    )


# -----------------------------
# BLOG POST TABLE
# -----------------------------

class BlogPost(db.Model):

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        unique=True,
        nullable=False
    )

    subtitle: Mapped[str] = mapped_column(
        nullable=False
    )

    date: Mapped[str] = mapped_column(
        nullable=False
    )

    body: Mapped[str] = mapped_column(
        nullable=False
    )

    author: Mapped[str] = mapped_column(
        nullable=False
    )

    img_url: Mapped[str] = mapped_column(
        nullable=False
    )

    comments: Mapped[list["Comment"]] = relationship(
        back_populates="parent_post"
    )


# -----------------------------
# COMMENT TABLE
# -----------------------------

class Comment(db.Model):

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    text: Mapped[str] = mapped_column(
        nullable=False
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"),
        nullable=False
    )

    post_id: Mapped[int] = mapped_column(
        ForeignKey("blog_post.id"),
        nullable=False
    )

    comment_author: Mapped["User"] = relationship(
        back_populates="comments"
    )

    parent_post: Mapped["BlogPost"] = relationship(
        back_populates="comments"
    )


# -----------------------------
# LOAD USER
# -----------------------------

@login_manager.user_loader
def load_user(user_id):

    return db.session.get(
        User,
        int(user_id)
    )


# -----------------------------
# ADMIN-ONLY DECORATOR
# -----------------------------

def admin_only(function):

    @wraps(function)
    def decorated_function(
        *args,
        **kwargs
    ):

        if (
            not current_user.is_authenticated
            or current_user.id != 1
        ):

            abort(403)

        return function(
            *args,
            **kwargs
        )

    return decorated_function


# -----------------------------
# REGISTER FORM
# -----------------------------

class RegisterForm(FlaskForm):

    name = StringField(
        "Name",
        validators=[
            DataRequired()
        ]
    )

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8)
        ]
    )

    submit = SubmitField(
        "Register"
    )


# -----------------------------
# LOGIN FORM
# -----------------------------

class LoginForm(FlaskForm):

    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email()
        ]
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired()
        ]
    )

    submit = SubmitField(
        "Login"
    )


# -----------------------------
# BLOG POST FORM
# -----------------------------

class CreatePostForm(FlaskForm):

    title = StringField(
        "Blog Post Title",
        validators=[
            DataRequired()
        ]
    )

    subtitle = StringField(
        "Subtitle",
        validators=[
            DataRequired()
        ]
    )

    author = StringField(
        "Your Name",
        validators=[
            DataRequired()
        ]
    )

    img_url = StringField(
        "Blog Image URL",
        validators=[
            DataRequired(),
            URL()
        ]
    )

    body = CKEditorField(
        "Blog Content",
        validators=[
            DataRequired()
        ]
    )

    submit = SubmitField(
        "Submit Post"
    )


# -----------------------------
# COMMENT FORM
# -----------------------------

class CommentForm(FlaskForm):

    comment_text = CKEditorField(
        "Comment",
        validators=[
            DataRequired()
        ]
    )

    submit = SubmitField(
        "Submit Comment"
    )


# -----------------------------
# CREATE DATABASE
# -----------------------------

with app.app_context():

    db.create_all()


# -----------------------------
# HOME
# -----------------------------

@app.route("/")
def home():

    result = db.session.execute(
        db.select(BlogPost)
    )

    all_posts = result.scalars().all()

    return render_template(
        "index.html",
        posts=all_posts
    )


# -----------------------------
# REGISTER
# -----------------------------

@app.route(
    "/register",
    methods=[
        "GET",
        "POST"
    ]
)
def register():

    form = RegisterForm()

    message = None

    if form.validate_on_submit():

        email = form.email.data.strip().lower()

        existing_user = db.session.execute(
            db.select(User).where(
                User.email == email
            )
        ).scalar_one_or_none()

        if existing_user:

            message = (
                "You've already signed up "
                "with that email."
            )

        else:

            hashed_password = generate_password_hash(
                form.password.data
            )

            new_user = User(
                name=form.name.data.strip(),
                email=email,
                password=hashed_password
            )

            db.session.add(
                new_user
            )

            try:

                db.session.commit()

                login_user(
                    new_user
                )

                return redirect(
                    url_for("home")
                )

            except IntegrityError:

                db.session.rollback()

                message = (
                    "You've already signed up "
                    "with that email."
                )

    return render_template(
        "register.html",
        form=form,
        message=message
    )


# -----------------------------
# LOGIN
# -----------------------------

@app.route(
    "/login",
    methods=[
        "GET",
        "POST"
    ]
)
def login():

    form = LoginForm()

    message = None

    if form.validate_on_submit():

        email = form.email.data.strip().lower()

        user = db.session.execute(
            db.select(User).where(
                User.email == email
            )
        ).scalar_one_or_none()

        if user is None:

            message = "User not found."

        elif check_password_hash(
            user.password,
            form.password.data
        ):

            login_user(
                user
            )

            return redirect(
                url_for("home")
            )

        else:

            message = "Incorrect password."

    return render_template(
        "login.html",
        form=form,
        message=message
    )


# -----------------------------
# LOGOUT
# -----------------------------

@app.route("/logout")
def logout():

    logout_user()

    return redirect(
        url_for("home")
    )


# -----------------------------
# SHOW POST + COMMENTS
# -----------------------------

@app.route(
    "/post/<int:post_id>",
    methods=[
        "GET",
        "POST"
    ]
)
def show_post(post_id):

    requested_post = db.get_or_404(
        BlogPost,
        post_id
    )

    comment_form = CommentForm()

    if comment_form.validate_on_submit():

        if not current_user.is_authenticated:

            return redirect(
                url_for("login")
            )

        new_comment = Comment(
            text=comment_form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post
        )

        db.session.add(
            new_comment
        )

        db.session.commit()

        return redirect(
            url_for(
                "show_post",
                post_id=requested_post.id
            )
        )

    return render_template(
        "post.html",
        post=requested_post,
        form=comment_form
    )


# -----------------------------
# NEW POST
# -----------------------------

@app.route(
    "/new-post",
    methods=[
        "GET",
        "POST"
    ]
)
@admin_only
def add_new_post():

    form = CreatePostForm()

    if form.validate_on_submit():

        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            author=form.author.data,
            img_url=form.img_url.data,
            body=form.body.data,
            date=datetime.now().strftime(
                "%B %d, %Y"
            )
        )

        db.session.add(
            new_post
        )

        db.session.commit()

        return redirect(
            url_for("home")
        )

    return render_template(
        "new-post.html",
        form=form,
        is_edit=False
    )


# -----------------------------
# EDIT POST
# -----------------------------

@app.route(
    "/edit-post/<int:post_id>",
    methods=[
        "GET",
        "POST"
    ]
)
@admin_only
def edit_post(post_id):

    post = db.get_or_404(
        BlogPost,
        post_id
    )

    form = CreatePostForm(
        obj=post
    )

    if form.validate_on_submit():

        post.title = form.title.data
        post.subtitle = form.subtitle.data
        post.author = form.author.data
        post.img_url = form.img_url.data
        post.body = form.body.data

        db.session.commit()

        return redirect(
            url_for(
                "show_post",
                post_id=post.id
            )
        )

    return render_template(
        "new-post.html",
        form=form,
        is_edit=True
    )


# -----------------------------
# DELETE POST
# -----------------------------

@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):

    post = db.get_or_404(
        BlogPost,
        post_id
    )

    db.session.delete(
        post
    )

    db.session.commit()

    return redirect(
        url_for("home")
    )


# -----------------------------
# RUN FLASK
# -----------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )