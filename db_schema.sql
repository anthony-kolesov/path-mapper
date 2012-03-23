create table if not exists tracks(id integer primary key autoincrement,
    name text);

create table if not exists track_points(id integer primary key autoincrement,
    lat integer not null, lon integer not null,
    elevation real, time text, course real, speed real, track integer);

