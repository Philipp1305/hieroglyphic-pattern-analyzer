------------------------------------------------------------------
-- T_IMAGES
------------------------------------------------------------------
-- TABLE
create table T_IMAGES(
	id					integer	not null,
	json				jsonb	not null,
	title				text	not null,
	img					bytea 	not null,
	file_name			text 	not null,
	mimetype			text 	not null,
	reading_direction 	numeric(1,0) default 0 not null,
	id_status 			number not null,
	constraint			T_IMAGES_PK primary key (id),
	constraint 			T_IMAGES_FK foreign key(id_status) references T_IMAGES_STATUS(id)
);

-- COMMENTS
comment on table t_images
is 'stores the images and more associated information';
comment on column t_images.id 
is 'Primary Key';
comment on column t_images.json
is 'stores the coco json uploaded with the image';
comment on column t_images.title
is 'title of the image';
comment on column t_images.img
is 'binary data of the image';
comment on column t_images.file_name
is 'original file name of the image';
comment on column t_images.mimetype
is 'mimetype of the image';
comment on column t_images.reading_direction 
is 'saves the reading direction (0 = left to right, 1 = right to left)';
comment on column t_images.id_status
is 'status - foreign key to t_images_status table';

-- SEQUENCE
create sequence T_IMAGES_SEQ
start with 1
increment by 1;

-- TRIGGER FUNCTION
create or replace function SET_T_IMAGES_ID()
returns trigger as $$
begin
    new.id := nextval('T_IMAGES_SEQ');
    return new;
end;
$$ language plpgsql;

-- TRIGGER
create or replace trigger T_IMAGES_TR
before insert on T_IMAGES
for each row
execute function SET_T_IMAGES_ID();

------------------------------------------------------------------
-- T_GARDINER_CODES
------------------------------------------------------------------
-- TABLE
create table T_GARDINER_CODES(
	id			integer not null,
	code		text,
	unicode		text,
	constraint	T_GARDINER_CODES_PK primary key (id)
);

-- COMMENTS
comment on table T_GARDINER_CODES
is 'stores the Gardiner codes for hieroglyphs';
comment on column t_gardiner_codes.id
is 'Primary Key';
comment on column t_gardiner_codes.code
is 'Gardiner code of the hieroglyph';
comment on column t_gardiner_codes.unicode
is 'Unicode representation of the hieroglyph';

-- SEQUENCE
create sequence T_GARDINER_CODES_SEQ
start with 1
increment by 1;

-- TRIGGER FUNCTION
create or replace function SET_T_GARDINER_CODES_ID()
returns trigger as $$
begin
    new.id := nextval('T_GARDINER_CODES_SEQ');
    return new;
end;
$$ language plpgsql;

-- TRIGGER
create or replace trigger T_GARDINER_CODES_TR
before insert on T_GARDINER_CODES
for each row
execute function SET_T_GARDINER_CODES_ID();

------------------------------------------------------------------
-- T_GLYPHES_RAW
------------------------------------------------------------------

-- TABLE
create table T_GLYPHES_RAW(
	id 			integer not null
	id_original	integer not null,
	id_image	integer not null,
	id_gardiner integer,
	bbox_x 		double precision not null,
	bbox_y 		double precision not null,
	bbox_height double precision not null,
	bbox_width 	double precision not null,
	constraint 	T_GLYPHES_RAW_PK primary key (id),
	constraint	T_GLYPHES_RAW_FK_IMAGE foreign key (id_image) references T_IMAGES(id),
	constraint 	T_GLYPHES_RAW_FK_GARDINER foreign key (id_gardiner) references T_GARDINER_CODES(id)
);

-- COMMENTS
comment on table T_GLYPHES_RAW
is 'stores the raw hieroglyph data extracted from the coco json';
comment on column t_glyphes_raw.id
is 'Primary Key - corresponds to the id in the coco json';
comment on column t_glyphes_raw.id_image
is 'Foreign Key to T_IMAGES table';
comment on column t_glyphes_raw.id_gardiner
is 'Foreign Key to T_GARDINER_CODES table';
comment on column t_glyphes_raw.bbox_x
is 'bounding box x coordinate';
comment on column t_glyphes_raw.bbox_y
is 'bounding box y coordinate';
comment on column t_glyphes_raw.bbox_height
is 'bounding box height';
comment on column t_glyphes_raw.bbox_width
is 'bounding box width';

-- SEQUENCE
create sequence T_GLYPHES_RAW_SEQ
start with 1
increment by 1;

-- TRIGGER FUNCTION
create or replace function SET_T_GLYPHES_RAW_ID()
returns trigger as $$
begin
    new.id := nextval('T_GLYPHES_RAW_SEQ');
    return new;
end;
$$ language plpgsql;

-- TRIGGER
create or replace trigger T_GLYPHES_RAW_TR
before insert on T_GLYPHES_RAW
for each row
execute function SET_T_GLYPHES_RAW_ID();

------------------------------------------------------------------
-- T_GLYPHES_SORTED
------------------------------------------------------------------

-- TABLE
create table T_GLYPHES_SORTED(
	id_glyph	integer not null,
	column		integer not null,
	row			integer not null,
	constraint	T_GLYPHES_SORTED_PK primary key (id_glyph, column, row)
	constraint 	T_GLYPHES_SORTED_FK foreign key (id_glyph) references T_GLYPHES_RAW(id)
);

-- COMMENTS
comment on table T_GLYPHES_SORTED
is 'stores the sorted hieroglyphs positions after applying the sorting algorithm';
comment on column t_glyphes_sorted.id_glyph
is 'Foreign Key to T_GLYPHES_RAW table';
comment on column t_glyphes_sorted.column
is 'column position after sorting';
comment on column t_glyphes_sorted.row
is 'row position after sorting';

------------------------------------------------------------------
-- T_IMAGES_STATUS
------------------------------------------------------------------

-- TABLE
create table T_IMAGES_STATUS(
	id integer 	not null,
	status text	not null,
	status_code not null,
	constraint 	T_IMAGES_STATUS_PK primary key (id),
	constraint 	T_IMAGES_STATUS_UQ unique (status_code)
);

-- COMMENTS
comment on table t_images_status
is 'stores the possible status of images (e.g., pending, processed)';
comment on column t_images_status.id
is 'Primary Key';
comment on column t_images_status.status
is 'text of status';
comment on column t_images_status.status_code
is 'code of status';

create sequence T_IMAGES_STATUS_SEQ
start with 1
increment by 1;

create or replace function SET_T_IMAGES_STATUS_ID()
returns trigger as $$
begin
    new.id := nextval('T_IMAGES_STATUS_SEQ');
    return new;
end;
$$ language plpgsql;

create or replace trigger T_IMAGES_STATUS_TR
before insert on T_IMAGES_STATUS
for each row
execute function SET_T_IMAGES_STATUS_ID();

-- Insert initial statuses
insert into T_IMAGES_STATUS(status, status_code)
values ('Uploaded', 'UPLOAD');

insert into T_IMAGES_STATUS(status, status_code)
values ('JSON processed', 'JSON');

insert into T_IMAGES_STATUS(status, status_code)
values ('Sorting', 'SORT_VALIDATE');

insert into T_IMAGES_STATUS(status, status_code)
values ('Sorted', 'SORT_VALIDATE');

insert into T_IMAGES_STATUS(status, status_code)
values ('N-Grams computed', 'NGRAMS');

insert into T_IMAGES_STATUS(status, status_code)
values ('Suffix-Tree computed', 'SUFFIX');