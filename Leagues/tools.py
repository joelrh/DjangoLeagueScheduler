import datetime


def convertDatetimeToString(o):
    DATE_FORMAT = "%Y-%m-%d"
    TIME_FORMAT = "%H:%M"

    if isinstance(o, datetime.date):
        return o.strftime(DATE_FORMAT)
    elif isinstance(o, datetime.time):
        return o.strftime(TIME_FORMAT)
    elif isinstance(o, datetime.datetime):
        return o.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))
