import random
import json
import phonenumbers
from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import StringField, HiddenField, RadioField, SelectField
from wtforms.validators import Length, ValidationError
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


app = Flask(__name__)
app.secret_key = 'Secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///main.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)


hours = {"1-2": "1-2 часа", "3-5": "3-5 часов", "5-7": "5-7 часов", "7-10": "7-10 часов"}
days = {"mon": "Понедельник", "tue": "Вторник", "wed": "Среда", "thu": "Четверг", "fri": "Пятница", "sat": "Суббота", "sun": "Воскресенье"}
week = {'sun': 'sunday', 'mon': 'monday', 'tue': 'tuesday', 'wed': 'wednesday', 'thu': 'thursday', 'fri': 'friday', 'sat': 'saturday'}
sort_types = {'0': 'В случайном порядке', '1': 'Сначала дорогие', '2': 'Сначала недорогие', '3': 'Сначала лучшие по рейтингу'}


teachers_goals = db.Table('teachers_goals',
                          db.Column('teacher_id', db.Integer, db.ForeignKey('teachers.id')),
                          db.Column('goal_id', db.Integer, db.ForeignKey('goals.id')))


class Goal(db.Model):
    __tablename__ = "goals"
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.String)
    goal = db.Column(db.String)
    pic = db.Column(db.String)
    teachers = db.relationship("Teacher", secondary=teachers_goals, back_populates="goals")


class Teacher(db.Model):
    __tablename__ = "teachers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    about = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    picture = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    goals = db.relationship("Goal", secondary=teachers_goals, back_populates="teachers")
    free = db.Column(db.String, nullable=False)


class Booking(db.Model):
    __tablename__ = "booking_records"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)
    day = db.Column(db.String, nullable=False)
    time = db.Column(db.Integer, nullable=False)
    teachers = db.relationship('Teacher')
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))


class RequestTeacher(db.Model):
    __tablename__ = "requests_records"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)
    goal = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)


def make_database():
    with open("data.txt", "r") as d:
        data = json.load(d)
    for link, goal in data['goals'].items():
        pic = data['emodji'][link]
        add_goal = Goal(link=link, goal=goal, pic=pic)
        db.session.add(add_goal)
    for teacher in data['teachers']:

        new_teacher = Teacher(id=teacher['id'], name=teacher['name'], about=teacher['about'], rating=teacher['rating'], picture=teacher['picture'], price=teacher['price'], free=json.dumps(teacher['free']))
        db.session.add(new_teacher)
        for goal in teacher['goals']:
            new_goal = Goal.query.filter(Goal.link == goal).scalar()
            new_teacher.goals.append(new_goal)
    db.session.commit()


def check_phone(form, field):
    number = form.clientPhone.data
    try:
        if not phonenumbers.is_valid_number(phonenumbers.parse(number, 'RU')):
            raise phonenumbers.NumberParseException(None, None)
    except phonenumbers.NumberParseException:
        raise ValidationError('Пожалуйста укажите номер телефона полностью (+7ХХХХХХХХХХ)')


def convert_day(day):
    for key, value in week.items():
        if value == day:
            return key


def add_callback(name, phone, goal, time):
    new_callback = RequestTeacher(name=name, phone=phone, goal=goal, time=time)
    db.session.add(new_callback)
    db.session.commit()


def add_record(name, phone, teacher_id, day, time):
    new_record = Booking(name=name, phone=phone, teacher_id=teacher_id, day=day, time=time)
    db.session.add(new_record)
    db.session.commit()


class SortTeachers(FlaskForm):
    sort_type = SelectField('Тип сортировки', choices=[(key, value) for key, value in sort_types.items()], default='0')


class RequestForm(FlaskForm):
    goals = db.session.query(Goal).all()
    goal_choices = {}
    for goal in goals:
        goal_choices[goal.link] = goal.goal
    clientName = StringField('Вас зовут', [Length(min=2, message='Пожалуйста укажите ваше имя')])
    clientPhone = StringField('Ваш телефон', [check_phone])
    time = RadioField('Сколько времени есть?', choices=[(key, value) for key, value in hours.items()], default='1-2')
    goals = RadioField('Какая цель занятий?', choices=[(key, value) for key, value in goal_choices.items()], default='travel')


class BookingForm(FlaskForm):
    clientName = StringField('Вас зовут', [Length(min=2, message='Пожалуйста укажите ваше имя')])
    clientPhone = StringField('Ваш телефон', [check_phone])
    clientWeekday = HiddenField()
    clientTime = HiddenField()
    clientTeacher = HiddenField()


@app.route('/')
def main():
    teachers = db.session.query(Teacher).all()
    goals = db.session.query(Goal).all()
    random_teachers_ids = set()
    while len(random_teachers_ids) < 6:
        random_teachers_ids.add(random.randint(0, len(teachers)-1))
    sorted_list = []
    for i in random_teachers_ids:
        sorted_list.append(teachers[i])
    return render_template('index.html', teachers=sorted_list, goals=goals)


@app.route('/all/', methods=['POST', 'GET'])
def all_teachers():
    form = SortTeachers()
    teachers = db.session.query(Teacher).all()
    if request.method == 'POST':
        sort_type = form.sort_type.data
        if sort_type == '1':
            teachers = db.session.query(Teacher).order_by(Teacher.price.desc()).all()
        if sort_type == '2':
            teachers = db.session.query(Teacher).order_by(Teacher.price).all()
        if sort_type == '3':
            teachers = db.session.query(Teacher).order_by(Teacher.rating.desc()).all()

    return render_template('all.html', teachers=teachers, form=form)


@app.route('/goals/<goal>/')
def show_goals(goal):
    target_goal = db.session.query(Goal).filter(Goal.link == goal).first()
    return render_template("goal.html", teachers=target_goal.teachers, goal=target_goal)


@app.route('/profiles/<int:teacher_id>/')
def show_profile(teacher_id):
    teacher = db.session.query(Teacher).get_or_404(teacher_id)
    free_time = json.loads(teacher.free)
    return render_template("profile.html", teacher=teacher, days=days, week=week, free=free_time)


@app.route('/request/', methods=['POST', 'GET'])
def make_request():
    form = RequestForm()
    if request.method == 'POST' and form.validate_on_submit():
        name = form.clientName.data
        phone = form.clientPhone.data
        goal = form.goals.data
        time = form.time.data
        add_callback(name, phone, goal, time)
        return render_template("request_done.html", name=name, phone=phone, goal=goal, time=hours.get(time))
    else:
        return render_template("request.html", form=form)


@app.route('/booking/<int:teacher_id>/<day>/<time>/', methods=['POST', 'GET'])
def booking(teacher_id, day, time):
    teacher = db.session.query(Teacher).get_or_404(teacher_id)
    what_day = convert_day(day)
    time_for_write = time + ":00"
    form = BookingForm(clientTime=time, clientWeekday=what_day, clientTeacher=teacher_id)
    if request.method == 'POST' and form.validate_on_submit():
        name = form.clientName.data
        phone = form.clientPhone.data
        add_record(name, phone, teacher_id, what_day, time_for_write)
        return render_template("booking_done.html", name=name, phone=phone, day=days.get(what_day), time=time, teacher_id=teacher_id)
    else:
        return render_template("booking.html", teacher_id=teacher.id, teacher=teacher, what_day=what_day, day=day, time=time, days=days, form=form)


if __name__ == '__main__':
    # make_database() - заполнение базы данными
    app.run()
